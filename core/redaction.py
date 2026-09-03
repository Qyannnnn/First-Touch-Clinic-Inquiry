import re

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine


analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()


# Singapore NRIC / FIN style
SG_ID_PATTERN = re.compile(
    r"\b[STFGM]\d{7}[A-Z]\b",
    re.IGNORECASE,
)

# Malaysian IC:
# 900101-14-5678
# or 900101145678
MY_IC_PATTERN = re.compile(
    r"\b\d{6}-?\d{2}-?\d{4}\b"
)


def redact_phi(text: str) -> str:
    # Deterministic ID protection first.
    safe_text = SG_ID_PATTERN.sub(
        "[REDACTED]",
        text,
    )

    safe_text = MY_IC_PATTERN.sub(
        "[REDACTED]",
        safe_text,
    )

    results = analyzer.analyze(
        text=safe_text,
        language="en",
        entities=[
            "PERSON",
            "PHONE_NUMBER",
            "EMAIL_ADDRESS",
        ],
    )

    anonymized = anonymizer.anonymize(
        text=safe_text,
        analyzer_results=results,
    )

    return anonymized.text