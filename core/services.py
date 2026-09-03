from .channel_rules import CHANNEL_RULES
from .models import FunnelEvent, Message, RiskAssessment
from .redaction import redact_phi
from .risk import assess_risk
from .llm_chat import generate_intake_reply

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
    for original in lead.messages.order_by("created_at"):
        Message.objects.create(
            patient_session=patient_session,
            sender=Message.Sender.PATIENT if original.sender == Message.Sender.GUEST else original.sender,
            content=original.content,
            redacted_content=original.redacted_content,
            origin_message=original,
        )

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

EMERGENCY_NOTICE = (
    "If this is an emergency, exit Nightingale and dial 999 "
    "for Emergency Services."
)


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

    try:
        reply = generate_intake_reply(
            redacted_text=redacted_text,
            patient_mode=False,
            risk_level=level,
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

    try:
        reply = generate_intake_reply(
            redacted_text=redacted_text,
            patient_mode=True,
            risk_level=level,
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