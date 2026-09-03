import io
import logging

from django.test import TestCase

from core.redaction import redact_phi


class RedactionTest(TestCase):

    def test_name_and_ic_are_removed_before_llm_use(self):
        raw = (
            "My name is John Doe and "
            "my IC is S1234567A."
        )

        safe = redact_phi(raw)

        self.assertNotIn(
            "John Doe",
            safe,
        )

        self.assertNotIn(
            "S1234567A",
            safe,
        )

    def test_raw_phi_is_not_logged(self):
        raw = (
            "My name is John Doe and "
            "my IC is S1234567A."
        )

        stream = io.StringIO()

        handler = logging.StreamHandler(
            stream
        )

        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

        try:
            redact_phi(raw)
        finally:
            root_logger.removeHandler(handler)

        logs = stream.getvalue()

        self.assertNotIn(
            "John Doe",
            logs,
        )

        self.assertNotIn(
            "S1234567A",
            logs,
        )