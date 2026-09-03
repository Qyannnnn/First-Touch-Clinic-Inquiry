from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import (
    Clinic,
    LeadSession,
    Patient,
    PatientSession,
)


class AccessControlTest(TestCase):

    def setUp(self):
        self.clinic = Clinic.objects.create(
            name="Test Clinic",
            slug="test-clinic",
        )

        self.lead_a = LeadSession.objects.create(
            clinic=self.clinic,
            source_channel="website_widget",
        )

        self.lead_b = LeadSession.objects.create(
            clinic=self.clinic,
            source_channel="instagram_comment",
        )

        self.user_a = User.objects.create_user(
            username="a@example.com",
            password="testpass123",
        )

        self.user_b = User.objects.create_user(
            username="b@example.com",
            password="testpass123",
        )

        self.patient_a = Patient.objects.create(
            user=self.user_a
        )

        self.patient_b = Patient.objects.create(
            user=self.user_b
        )

        self.session_a = PatientSession.objects.create(
            patient=self.patient_a,
            clinic=self.clinic,
            origin_lead_session=self.lead_a,
        )

        self.session_b = PatientSession.objects.create(
            patient=self.patient_b,
            clinic=self.clinic,
            origin_lead_session=self.lead_b,
        )

    def test_patient_a_cannot_fetch_patient_b_session(self):
        self.client.force_login(
            self.user_a
        )

        client_session = self.client.session
        client_session[
            "patient_session_id"
        ] = str(self.session_a.id)
        client_session.save()

        response = self.client.get(
            reverse(
                "patient_chat",
                args=[self.session_b.id],
            )
        )

        self.assertIn(
            response.status_code,
            [403, 404],
        )

    def test_patient_cannot_access_staff_triage_queue(self):
        self.client.force_login(
            self.user_a
        )

        response = self.client.get(
            "/staff/core/escalation/"
        )

        self.assertNotEqual(
            response.status_code,
            200,
        )

    def test_staff_can_access_admin(self):
        staff = User.objects.create_superuser(
            username="staff",
            email="staff@example.com",
            password="staffpass123",
        )

        self.client.force_login(staff)

        response = self.client.get(
            "/staff/core/patient/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )