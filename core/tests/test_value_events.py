from django.test import TestCase

from core.models import (
    Clinic,
    FunnelEvent,
    LeadSession,
)
from core.services import emit


class ValueEventTest(TestCase):

    def test_value_event_is_persisted_and_counted_from_database(self):
        clinic = Clinic.objects.create(
            name="Test Clinic",
            slug="test-clinic",
        )

        lead = LeadSession.objects.create(
            clinic=clinic,
            source_channel="instagram_comment",
        )

        emit(
            lead,
            FunnelEvent.EventType.VALUE_EVENT,
            {
                "value_type": "question_preparation",
            },
        )

        database_count = FunnelEvent.objects.filter(
            lead_session=lead,
            event_type=FunnelEvent.EventType.VALUE_EVENT,
        ).count()

        self.assertEqual(database_count, 1)

        event = FunnelEvent.objects.get(
            lead_session=lead,
            event_type=FunnelEvent.EventType.VALUE_EVENT,
        )

        self.assertEqual(
            event.metadata["value_type"],
            "question_preparation",
        )