from django.test import TestCase
from django.urls import reverse

from core.llm_memory import MemoryExtraction, MemoryFact
from core.models import (
    Clinic,
    LeadSession,
    MemoryItem,
    Message,
    PatientSession,
)
from unittest.mock import patch


class GuestToPatientConversionTest(TestCase):

    @patch("core.services.extract_memory_facts")
    def test_guest_context_survives_conversion(
        self,
        mock_extract,
    ):
        mock_extract.return_value = MemoryExtraction(
            facts=[
                MemoryFact(
                    kind="symptom",
                    value="headache",
                    status="active",
                )
            ]
        )

        clinic = Clinic.objects.create(
            name="Test Clinic",
            slug="test-clinic",
        )

        lead = LeadSession.objects.create(
            clinic=clinic,
            source_channel="instagram_ad_click",
            campaign_id="ivf_over40",
            landing_context="headache concern",
        )

        guest_message = Message.objects.create(
            lead_session=lead,
            sender=Message.Sender.GUEST,
            content="I have a headache.",
            redacted_content="I have a headache.",
        )

        response = self.client.post(
            reverse("convert", args=[lead.id]),
            {
                "email": "patient@example.com",
                "phone": "0123456789",
                "consent": "yes",
            },
        )

        self.assertEqual(response.status_code, 302)

        patient_session = PatientSession.objects.get(
            origin_lead_session=lead
        )

        self.assertEqual(
            patient_session.origin_lead_session.source_channel,
            "instagram_ad_click",
        )

        self.assertEqual(
            patient_session.origin_lead_session.campaign_id,
            "ivf_over40",
        )

        copied = Message.objects.get(
            patient_session=patient_session,
            origin_message=guest_message,
        )

        self.assertEqual(
            copied.content,
            "I have a headache.",
        )

        memory = MemoryItem.objects.get(
            patient_session=patient_session,
            kind="symptom",
            value="headache",
        )

        # Provenance must point to ORIGINAL GuestMessage.
        self.assertEqual(
            memory.provenance_pointer,
            guest_message,
        )