from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from core.llm_memory import (
    MemoryExtraction,
    MemoryFact,
)
from core.models import (
    Clinic,
    LeadSession,
    MemoryItem,
    Message,
    Patient,
    PatientSession,
)
from core.services import update_living_memory


class MemoryMutationTest(TestCase):

    @patch("core.services.extract_memory_facts")
    def test_advil_active_then_stopped_preserves_provenance(
        self,
        mock_extract,
    ):
        clinic = Clinic.objects.create(
            name="Test Clinic",
            slug="test-clinic",
        )

        lead = LeadSession.objects.create(
            clinic=clinic,
            source_channel="website_widget",
        )

        user = User.objects.create_user(
            username="patient@example.com"
        )

        patient = Patient.objects.create(
            user=user
        )

        session = PatientSession.objects.create(
            patient=patient,
            clinic=clinic,
            origin_lead_session=lead,
        )

        message_one = Message.objects.create(
            patient_session=session,
            sender=Message.Sender.PATIENT,
            content="I take Advil.",
            redacted_content="I take Advil.",
        )

        mock_extract.return_value = MemoryExtraction(
            facts=[
                MemoryFact(
                    kind="medication",
                    value="Advil",
                    status="active",
                )
            ]
        )

        update_living_memory(message_one)

        active_memory = MemoryItem.objects.get(
            patient_session=session,
            kind="medication",
            value="Advil",
            status="active",
        )

        self.assertEqual(
            active_memory.provenance_pointer,
            message_one,
        )

        message_two = Message.objects.create(
            patient_session=session,
            sender=Message.Sender.PATIENT,
            content="Actually I stopped last week.",
            redacted_content="Actually I stopped last week.",
        )

        mock_extract.return_value = MemoryExtraction(
            facts=[
                MemoryFact(
                    kind="medication",
                    value="Advil",
                    status="stopped",
                )
            ]
        )

        update_living_memory(message_two)

        active_memory.refresh_from_db()

        self.assertEqual(
            active_memory.status,
            "superseded",
        )

        stopped_memory = MemoryItem.objects.get(
            patient_session=session,
            kind="medication",
            value="Advil",
            status="stopped",
        )

        self.assertEqual(
            stopped_memory.provenance_pointer,
            message_two,
        )

        # Both historical states remain.
        self.assertEqual(
            MemoryItem.objects.filter(
                patient_session=session,
                kind="medication",
                value="Advil",
            ).count(),
            2,
        )