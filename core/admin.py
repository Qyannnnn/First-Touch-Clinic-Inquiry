from django.contrib import admin
from .models import Clinic, LeadSession, Patient, Consent, PatientSession, Message, FunnelEvent, MemoryItem, RiskAssessment, Escalation

for model in [Clinic, LeadSession, Patient, Consent, PatientSession, Message, FunnelEvent, MemoryItem, RiskAssessment, Escalation]:
    admin.site.register(model)
