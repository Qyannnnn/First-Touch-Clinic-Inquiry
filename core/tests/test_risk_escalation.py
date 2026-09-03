from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import (
    Clinic,
    LeadSession,
    Message,
    Patient,
    PatientSession,
    RiskAssessment,
)
from core.risk import assess_risk
from core.services import risk_aware_patient_reply


class RiskEscalationTest(TestCase):

    def test_crushing_chest_pain_is_always_high(self):
        result = assess_risk(
            "I have crushing chest pain."
        )

        self.assertEqual(
            result.level,
            "HIGH",
        )

    @patch("core.services.generate_intake_reply")
    def test_high_risk_response_requires_escalation(
        self,
        mock_reply,
    ):
        mock_reply.return_value = (
            "Please seek urgent medical attention now."
        )

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

        message = Message.objects.create(
            patient_session=session,
            sender=Message.Sender.PATIENT,
            content="I have crushing chest pain.",
            redacted_content="I have crushing chest pain.",
        )

        assessment = RiskAssessment.objects.create(
            message=message,
            risk_level="high",
            risk_reason="Urgent symptom",
            confidence=1.0,
        )

        reply = risk_aware_patient_reply(
            message.content,
            assessment,
        )

        self.assertIn(
            "urgent medical attention",
            reply.lower(),
        )

        self.assertIn(
            "dial 999",
            reply.lower(),
        )

        self.client.force_login(user)

        client_session = self.client.session
        client_session[
            "patient_session_id"
        ] = str(session.id)
        client_session.save()

        response = self.client.get(
            reverse(
                "patient_chat",
                args=[session.id],
            )
        )

        self.assertTrue(
            response.context[
                "show_send_to_clinic"
            ]
        )