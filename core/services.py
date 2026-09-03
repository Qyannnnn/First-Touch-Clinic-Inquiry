from .channel_rules import CHANNEL_RULES
from .models import FunnelEvent, MemoryItem, Message, RiskAssessment
from .redaction import redact_phi
from .risk import assess_risk
from .llm_chat import generate_intake_reply
from .llm_memory import extract_memory_facts

VALUE_KEYWORDS = ("what should i ask", "questions", "prepare", "egg freezing")

def opening_for(lead):
    rule = CHANNEL_RULES.get(lead.source_channel, CHANNEL_RULES["default"])
    context = lead.landing_context or "the topic that brought you here"
    return rule["opening"].format(context=context)

def guest_reply(text):
    low = text.lower()
    if "doctor" in low and "real" in low:
        return ("I’m Nightingale AI, not a doctor. I can provide general information and help you prepare questions. "
                "A human clinic team becomes involved when you choose to send your concern securely or when the system identifies that human review is needed."), True
    if any(k in low for k in VALUE_KEYWORDS):
        return ("Here are four useful questions you could prepare for the clinic: What does the process involve? "
                "What factors should I discuss with a clinician? What timeline should I expect? What costs and follow-up should I ask about?"), True
    return ("I can help with general information and question preparation while you’re a guest. If your question is about your own symptoms or needs clinical assessment, I’ll help you move to the secure patient flow instead of trying to diagnose you here."), False

def emit(lead, event_type, metadata=None):
    return FunnelEvent.objects.create(lead_session=lead, event_type=event_type, metadata=metadata or {})

def copy_guest_messages_to_patient(lead, patient_session):
    copied_messages = []

    for original in lead.messages.order_by("created_at"):
        copied = Message.objects.create(
            patient_session=patient_session,
            sender=(
                Message.Sender.PATIENT
                if original.sender == Message.Sender.GUEST
                else original.sender
            ),
            content=original.content,
            redacted_content=original.redacted_content,
            origin_message=original,
        )

        copied_messages.append(copied)

    return copied_messages

def process_incoming_message(message):
    """
    Safety processing for a guest/patient message.

    1. Redact PII for safe downstream AI use.
    2. Run deterministic + semantic risk assessment.
    3. Persist the RiskAssessment.
    """

    if message.sender not in {
        Message.Sender.GUEST,
        Message.Sender.PATIENT,
    }:
        return None

    # Create and store the safe AI-facing version
    message.redacted_content = redact_phi(message.content)

    message.save(
        update_fields=["redacted_content"]
    )

    # Run the full risk pipeline
    risk = assess_risk(message.content)

    assessment, _ = RiskAssessment.objects.update_or_create(
        message=message,
        defaults={
            "risk_level": risk.level.lower(),
            "risk_reason": risk.reason,
            "confidence": risk.confidence,
        },
    )

    return assessment

def update_living_memory(message):
    """
    Extract structured memory from a PatientSession message.

    Previous facts are preserved rather than overwritten so that
    provenance remains traceable.
    """

    if (
        message.sender != Message.Sender.PATIENT
        or not message.patient_session_id
    ):
        return []

    safe_text = (
        message.redacted_content
        or redact_phi(message.content)
    )

    try:
        extraction = extract_memory_facts(
            safe_text
        )
    except Exception:
        # Memory extraction failure must never break the chat.
        return []

    created_items = []

    for fact in extraction.facts:
        value = fact.value.strip()

        if not value:
            continue

        # Look for an existing current version of the same fact.
        existing = (
            MemoryItem.objects
            .filter(
                patient_session=message.patient_session,
                kind=fact.kind,
                value__iexact=value,
            )
            .exclude(status="superseded")
            .order_by("-updated_at")
            .first()
        )

        # Nothing changed: don't create duplicates.
        if (
            existing
            and existing.status == fact.status
        ):
            continue

        # Preserve the previous version instead of deleting it.
        if existing:
            existing.status = "superseded"
            existing.save(
                update_fields=["status"]
            )

        # Chief complaint should normally have one current version.
        if fact.kind == "chief_complaint":
            (
                MemoryItem.objects
                .filter(
                    patient_session=message.patient_session,
                    kind="chief_complaint",
                )
                .exclude(status="superseded")
                .update(status="superseded")
            )

        provenance_message = (
            message.origin_message
            if message.origin_message
            else message
        )

        item = MemoryItem.objects.create(
            patient_session=message.patient_session,
            kind=fact.kind,
            value=value,
            status=fact.status,
            provenance_pointer=provenance_message,
        )

        created_items.append(item)

    return created_items

EMERGENCY_NOTICE = (
    "If this is an emergency, exit Nightingale and dial 999 "
    "for Emergency Services."
)

def build_recent_context(message, limit=6):
    """
    Build a privacy-safe recent conversation for Gemini.

    User messages use redacted_content.
    AI messages use their generated content.
    """

    if message.patient_session_id:
        queryset = Message.objects.filter(
            patient_session=message.patient_session
        )

    elif message.lead_session_id:
        queryset = Message.objects.filter(
            lead_session=message.lead_session
        )

    else:
        return ""

    # Do not repeat the current message because we send it separately.
    recent = list(
        queryset.exclude(id=message.id)
        .order_by("-created_at")[:limit]
    )

    recent.reverse()

    lines = []

    for item in recent:
        if item.sender == Message.Sender.AI:
            role = "Nightingale"
            safe_content = item.content
        else:
            role = "User"
            safe_content = (
                item.redacted_content
                or redact_phi(item.content)
            )

        lines.append(
            f"{role}: {safe_content}"
        )

    return "\n".join(lines)

def risk_aware_guest_reply(text, assessment):
    """
    Gemini produces the conversational response.
    Python controls privacy and safety context.
    """

    redacted_text = redact_phi(text)

    level = (
        assessment.risk_level
        if assessment
        else "ambiguous"
    )

    conversation_context = ""

    if assessment:
        conversation_context = build_recent_context(
            assessment.message
        )

    try:
        reply = generate_intake_reply(
            redacted_text=redacted_text,
            patient_mode=False,
            risk_level=level,
            conversation_context=conversation_context,
        )

    except Exception:
        # Safe fallback if Gemini is unavailable
        return (
            "I'm unable to safely complete that response right now. "
            "Please contact the clinic if you need help."
        ), False

    # Mandatory deterministic emergency notice
    if level == "high":
        if EMERGENCY_NOTICE not in reply:
            reply = f"{reply}\n\n{EMERGENCY_NOTICE}"

    # LOW guest conversations count as useful guest value
    is_value = level == "low"

    return reply, is_value


def risk_aware_patient_reply(text, assessment):
    """
    Gemini produces the conversational patient response.
    Python controls privacy and safety context.
    """

    redacted_text = redact_phi(text)

    level = (
        assessment.risk_level
        if assessment
        else "ambiguous"
    )

    conversation_context = ""

    if assessment:
        conversation_context = build_recent_context(
            assessment.message
        )

    try:
        reply = generate_intake_reply(
            redacted_text=redacted_text,
            patient_mode=True,
            risk_level=level,
            conversation_context=conversation_context,
        )

    except Exception:
        # Conservative fallback
        if level == "high":
            return (
                "I'm unable to safely complete this response right now. "
                "Please seek urgent medical attention.\n\n"
                f"{EMERGENCY_NOTICE}"
            )

        return (
            "I'm unable to safely complete that response right now. "
            "Please contact the clinic for further assistance."
        )

    # Mandatory emergency wording can never be omitted
    if level == "high":
        if EMERGENCY_NOTICE not in reply:
            reply = f"{reply}\n\n{EMERGENCY_NOTICE}"

    return reply