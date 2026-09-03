from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Clinic, Consent, FunnelEvent, LeadSession, MemoryItem, Message, Patient, PatientSession, RiskAssessment
from .services import (
    copy_guest_messages_to_patient,
    emit,
    guest_reply,
    opening_for,
    process_incoming_message,
    risk_aware_guest_reply,
    risk_aware_patient_reply,
    update_living_memory,
    create_clinic_escalation,
)

def home(request):
    clinic, _ = Clinic.objects.get_or_create(name="Nightingale Demo Clinic", slug="nightingale-demo")
    return render(request, "acquisition.html", {"clinic": clinic})


def simulate_acquisition(request):
    if request.method != "POST":
        return redirect("home")
    clinic = get_object_or_404(Clinic, id=request.POST["clinic_id"])
    channel = request.POST.get("source_channel", "website_widget")
    handle = request.POST.get("social_handle", "").strip()
    identity = LeadSession.IdentityLevel.SOCIAL_HANDLE if handle else LeadSession.IdentityLevel.ANONYMOUS
    lead = LeadSession.objects.create(
        clinic=clinic,
        source_channel=channel,
        campaign_id=request.POST.get("campaign_id", ""),
        creative=request.POST.get("creative", ""),
        identity_level=identity,
        social_handle=handle,
        landing_context=request.POST.get("landing_context", ""),
    )
    emit(lead, FunnelEvent.EventType.VISITOR)
    Message.objects.create(lead_session=lead, sender=Message.Sender.AI, content=opening_for(lead))
    request.session["lead_id"] = str(lead.id)
    return redirect("guest_chat", lead_id=lead.id)


def guest_chat(request, lead_id):
    lead = get_object_or_404(LeadSession, id=lead_id)
    return render(request, "guest_chat.html", {
        "lead": lead,
        "messages": lead.messages.order_by("created_at"),
        "has_value": lead.events.filter(event_type=FunnelEvent.EventType.VALUE_EVENT).exists(),
    })


def guest_send(request, lead_id):
    lead = get_object_or_404(LeadSession, id=lead_id)
    if request.method == "POST":
        text = request.POST.get("message", "").strip()
        if text:
            first_guest = not lead.messages.filter(sender=Message.Sender.GUEST).exists()

            guest_message = Message.objects.create(
                lead_session=lead,
                sender=Message.Sender.GUEST,
                content=text,
            )

            assessment = process_incoming_message(
                guest_message
            )

            if first_guest:
                emit(
                    lead,
                    FunnelEvent.EventType.CONVERSATION_STARTED
                )

            reply, is_value = risk_aware_guest_reply(
                text,
                assessment,
            )
            Message.objects.create(lead_session=lead, sender=Message.Sender.AI, content=reply)
            if is_value and not lead.events.filter(event_type=FunnelEvent.EventType.VALUE_EVENT).exists():
                emit(lead, FunnelEvent.EventType.VALUE_EVENT, {"value_type": "question_preparation"})
    return redirect("guest_chat", lead_id=lead.id)


def trust_transition(request, lead_id):
    lead = get_object_or_404(LeadSession, id=lead_id)
    if not lead.events.filter(event_type=FunnelEvent.EventType.AUTH_STARTED).exists():
        emit(lead, FunnelEvent.EventType.AUTH_STARTED)
    return render(request, "convert.html", {"lead": lead})


@transaction.atomic
def convert(request, lead_id):
    lead = get_object_or_404(LeadSession, id=lead_id)
    if request.method != "POST":
        return redirect("trust_transition", lead_id=lead.id)
    if request.POST.get("consent") != "yes":
        return render(request, "convert.html", {"lead": lead, "error": "Consent is required to create a PatientSession."})

    email = request.POST.get("email", "").strip().lower()
    phone = request.POST.get("phone", "").strip()
    user, _ = User.objects.get_or_create(username=email, defaults={"email": email})
    patient, _ = Patient.objects.get_or_create(user=user, defaults={"phone": phone})
    if phone and patient.phone != phone:
        patient.phone = phone
        patient.save(update_fields=["phone"])

    Consent.objects.create(patient=patient, clinic=lead.clinic, share_health_info=True)
    emit(lead, FunnelEvent.EventType.CONSENTED)
    patient_session = PatientSession.objects.create(patient=patient, clinic=lead.clinic, origin_lead_session=lead)
    copied_messages = copy_guest_messages_to_patient(
        lead,
        patient_session,
    )

    for copied_message in copied_messages:
        if copied_message.sender == Message.Sender.PATIENT:
            update_living_memory(
                copied_message
            )
    lead.converted_at = timezone.now()
    lead.save(update_fields=["converted_at"])
    emit(lead, FunnelEvent.EventType.PATIENT_CREATED)
    request.session["patient_session_id"] = str(patient_session.id)
    return redirect("patient_chat", session_id=patient_session.id)


def patient_chat(request, session_id):
    session = get_object_or_404(
        PatientSession,
        id=session_id,
    )

    memory_items = (
        MemoryItem.objects
        .filter(patient_session=session)
        .exclude(status="superseded")
        .order_by("kind", "updated_at")
    )

    latest_patient_message = (
        session.messages
        .filter(sender=Message.Sender.PATIENT)
        .order_by("-created_at")
        .first()
    )

    latest_assessment = None
    show_send_to_clinic = False

    if latest_patient_message:
        latest_assessment = (
            RiskAssessment.objects
            .filter(message=latest_patient_message)
            .first()
        )

        if (
            latest_assessment
            and latest_assessment.risk_level
            in {"medium", "high", "ambiguous"}
        ):
            show_send_to_clinic = True

    sent_escalation = request.session.pop(
        "sent_escalation",
        None,
    )

    return render(
        request,
        "patient_chat.html",
        {
            "patient_session": session,
            "messages": session.messages.order_by(
                "created_at"
            ),
            "memory_items": memory_items,
            "latest_patient_message": latest_patient_message,
            "latest_assessment": latest_assessment,
            "show_send_to_clinic": show_send_to_clinic,
            "sent_escalation": sent_escalation,
        },
    )

def patient_send(request, session_id):
    session = get_object_or_404(
        PatientSession,
        id=session_id,
    )

    if request.method == "POST":
        text = request.POST.get(
            "message",
            "",
        ).strip()

        if text:
            patient_message = Message.objects.create(
                patient_session=session,
                sender=Message.Sender.PATIENT,
                content=text,
            )

            assessment = process_incoming_message(
                patient_message
            )

            update_living_memory(
                patient_message
            )
            
            reply = risk_aware_patient_reply(
                text,
                assessment,
            )

            Message.objects.create(
                patient_session=session,
                sender=Message.Sender.AI,
                content=reply,
            )

    return redirect(
        "patient_chat",
        session_id=session.id,
    )

def send_to_clinic(request, session_id):
    session = get_object_or_404(
        PatientSession,
        id=session_id,
    )

    if request.method != "POST":
        return redirect(
            "patient_chat",
            session_id=session.id,
        )

    message_id = request.POST.get(
        "message_id"
    )

    triggering_message = get_object_or_404(
        Message,
        id=message_id,
        patient_session=session,
        sender=Message.Sender.PATIENT,
    )

    escalation = create_clinic_escalation(
        patient_session=session,
        triggering_message=triggering_message,
    )

    request.session["sent_escalation"] = (
        escalation.id
    )

    return redirect(
        "patient_chat",
        session_id=session.id,
    )
