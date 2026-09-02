import uuid

from django.contrib.auth.models import User
from django.db import models

class Clinic(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

class LeadSession(models.Model):
    class IdentityLevel(models.TextChoices):
        ANONYMOUS = "anonymous", "Anonymous"
        SOCIAL_HANDLE = "social_handle", "Social handle known"
        EMAIL_KNOWN = "email_known", "Email known"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    source_channel = models.CharField(max_length=50)
    campaign_id = models.CharField(max_length=100, blank=True)
    creative = models.CharField(max_length=100, blank=True)
    identity_level = models.CharField(max_length=30, choices=IdentityLevel.choices, default=IdentityLevel.ANONYMOUS)
    social_handle = models.CharField(max_length=100, blank=True)
    landing_context = models.TextField(blank=True)
    landing_timestamp = models.DateTimeField(auto_now_add=True)
    converted_at = models.DateTimeField(null=True, blank=True)

class Patient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)

class Consent(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    share_health_info = models.BooleanField(default=False)
    consented_at = models.DateTimeField(auto_now_add=True)

class PatientSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    origin_lead_session = models.ForeignKey(LeadSession, on_delete=models.PROTECT, related_name="patient_sessions")
    created_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    class Sender(models.TextChoices):
        GUEST = "guest", "Guest"
        PATIENT = "patient", "Patient"
        AI = "ai", "Nightingale AI"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead_session = models.ForeignKey(LeadSession, null=True, blank=True, on_delete=models.CASCADE, related_name="messages")
    patient_session = models.ForeignKey(PatientSession, null=True, blank=True, on_delete=models.CASCADE, related_name="messages")
    sender = models.CharField(max_length=20, choices=Sender.choices)
    content = models.TextField()
    redacted_content = models.TextField(blank=True)
    # When a permitted GuestMessage is carried into PatientSession, this preserves
    # the original source instead of pretending the copied message is the source.
    origin_message = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="derived_messages")
    created_at = models.DateTimeField(auto_now_add=True)

class FunnelEvent(models.Model):
    class EventType(models.TextChoices):
        VISITOR = "visitor", "Visitor"
        CONVERSATION_STARTED = "conversation_started", "Conversation started"
        VALUE_EVENT = "value_event", "Value event"
        AUTH_STARTED = "auth_started", "Auth started"
        CONSENTED = "consented", "Consented"
        PATIENT_CREATED = "patient_created", "Patient created"
        ESCALATION_SENT = "escalation_sent", "Escalation sent"

    lead_session = models.ForeignKey(LeadSession, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class MemoryItem(models.Model):
    patient_session = models.ForeignKey(PatientSession, on_delete=models.CASCADE, related_name="memory_items")
    kind = models.CharField(max_length=50)
    value = models.CharField(max_length=500)
    status = models.CharField(max_length=50, default="active")
    provenance_pointer = models.ForeignKey(Message, on_delete=models.PROTECT, related_name="memory_provenance")
    updated_at = models.DateTimeField(auto_now=True)

class RiskAssessment(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        AMBIGUOUS = "ambiguous", "Ambiguous"

    message = models.OneToOneField(
        Message,
        on_delete=models.CASCADE,
    )

    risk_level = models.CharField(
        max_length=12,
        choices=RiskLevel.choices,
    )

    risk_reason = models.CharField(
        max_length=500,
    )

    confidence = models.FloatField()

    assessed_at = models.DateTimeField(
        auto_now_add=True,
    )

class Escalation(models.Model):
    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        UNDER_REVIEW = "under_review", "Under review"
        RESPONDED = "responded", "Responded"

    patient_session = models.ForeignKey(PatientSession, on_delete=models.CASCADE, related_name="escalations")
    triggering_message = models.ForeignKey(Message, on_delete=models.PROTECT)
    triage_summary = models.JSONField(default=list)
    profile_snapshot = models.JSONField(default=dict)
    provenance_points = models.JSONField(default=list)
    acquisition_context = models.JSONField(default=dict)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.SENT)
    clinician_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)