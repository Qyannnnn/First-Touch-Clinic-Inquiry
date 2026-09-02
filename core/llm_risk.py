import os
from typing import Literal

from google import genai
from pydantic import BaseModel, Field


client = genai.Client()

MODEL_NAME = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite",
)


class SemanticRiskResult(BaseModel):
    level: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
        "AMBIGUOUS",
    ]

    reason: str

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

SYSTEM_PROMPT = """
You are an internal safety classification component for a healthcare
intake system.

Your output is INTERNAL METADATA and is not medical advice.

Your only job is to classify urgency and safety risk.

Do not diagnose.
Do not suggest a diagnosis.
Do not name diseases or possible diseases.
Do not give differential diagnoses.
Do not speculate about the cause of symptoms.
Do not recommend medication.
Do not provide treatment.
Do not write a conversational response to the patient.

The reason field must describe ONLY the observed safety concern.

Good reason:
"Potentially serious chest-related symptom requiring urgent assessment."

Bad reason:
"This could be a heart attack."

Good reason:
"Reported severe breathing difficulty."

Bad reason:
"This may indicate asthma or respiratory failure."

Classify into exactly one level:

LOW:
No clear urgent safety concern.

MEDIUM:
Potentially concerning symptoms or situation that should be reviewed
by a healthcare professional, but no clear immediate emergency.

HIGH:
Possible immediate danger, severe symptoms, or self-harm risk.

AMBIGUOUS:
The message could represent a significant safety issue, but there is
not enough information to classify confidently.

When uncertain between LOW and a higher-risk category,
do not choose LOW.

Return:
- level
- short non-diagnostic reason
- confidence between 0 and 1
"""

def assess_semantic_risk(
    redacted_text: str,
) -> SemanticRiskResult:

    prompt = f"""
{SYSTEM_PROMPT}

Patient message:
{redacted_text}
"""

    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": SemanticRiskResult.model_json_schema(),
        },
    )

    return SemanticRiskResult.model_validate_json(
        interaction.output_text
    )