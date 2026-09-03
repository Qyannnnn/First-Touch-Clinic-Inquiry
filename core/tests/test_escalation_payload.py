from django.contrib.auth.models import User
from django.test import TestCase

from core.models import (
    Clinic,
    Escalation,
    LeadSession,
    MemoryItem,
    Message,
    Patient,
    PatientSession,
)
from core.services import create_clinic_escalation


class EscalationPayloadTest(TestCase):

    def test_send_to_clinic_persists_complete_payload(self):
        clinic = Clinic.objects.create(
            name="Test Clinic",
            slug="test-clinic",
        )

        lead = LeadSession.objects.create(
            clinic=clinic,
            source_channel="instagram_ad_click",
            campaign_id="campaign-123",
            creative="creative-a",
            landing_context="headache",
        )

        user = User.objects.create_user(
            username="patient@example.com"
        )

        patient = Patient.objects.create(
            user=user,
        )

        session = PatientSession.objects.create(
            patient=patient,
            clinic=clinic,
            origin_lead_session=lead,
        )

        trigger = Message.objects.create(
            patient_session=session,
            sender=Message.Sender.PATIENT,
            content="My chest feels funny.",
            redacted_content="My chest feels funny.",
        )

        MemoryItem.objects.create(
            patient_session=session,
            kind="symptom",
            value="headache",
            status="active",
            provenance_pointer=trigger,
        )

        escalation = create_clinic_escalation(
            patient_session=session,
            triggering_message=trigger,
        )

        escalation.refresh_from_db()

        self.assertEqual(
            escalation.triggering_message,
            trigger,
        )

        self.assertTrue(
            len(escalation.triage_summary) >= 1
        )

        self.assertIn(
            "symptom",
            escalation.profile_snapshot,
        )

        self.assertTrue(
            len(escalation.provenance_points) >= 1
        )

        self.assertEqual(
            escalation.acquisition_context[
                "source_channel"
            ],
            "instagram_ad_click",
        )

        self.assertEqual(
            escalation.acquisition_context[
                "campaign_id"
            ],
            "campaign-123",
        )

        self.assertTrue(
            Escalation.objects.filter(
                id=escalation.id
            ).exists()
        )