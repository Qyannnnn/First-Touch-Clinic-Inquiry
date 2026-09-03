import os
from typing import Literal

from google import genai
from pydantic import BaseModel, Field


client = genai.Client()

MODEL_NAME = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite",
)


class MemoryFact(BaseModel):
    kind: Literal[
        "chief_complaint",
        "symptom",
        "timeline",
        "medication",
        "allergy",
    ]

    value: str = Field(min_length=1)

    status: Literal[
        "active",
        "reported",
        "stopped",
        "resolved",
    ]


class MemoryExtraction(BaseModel):
    facts: list[MemoryFact]


MEMORY_PROMPT = """
You extract structured Living Memory from a patient's message.

This is NOT a diagnostic task.

Only extract facts explicitly stated by the patient.

Allowed kinds:
- chief_complaint
- symptom
- timeline
- medication
- allergy

Rules:
- Never diagnose.
- Never infer a disease.
- Never invent information.
- Never infer medication that was not mentioned.
- Keep values short and factual.
- If no useful memory exists, return an empty facts list.
- Do not include names, phone numbers, emails or identifiers.
- Preserve medication/allergy names if stated.
- A symptom currently happening should normally be "active".
- A historical/descriptive fact may be "reported".
- If the patient explicitly stopped a medication, use "stopped".
- If the patient explicitly says a symptom has ended, use "resolved".

Examples:

Message:
"I've had headaches for three days."

Facts:
- symptom: headache, active
- timeline: headache for three days, reported

Message:
"I'm taking Advil."

Facts:
- medication: Advil, active

Message:
"I stopped taking Advil yesterday."

Facts:
- medication: Advil, stopped

Message:
"I'm allergic to penicillin."

Facts:
- allergy: penicillin, active

Message:
"I'm just worried about this."

Facts:
[]
"""


def extract_memory_facts(
    redacted_text: str,
) -> MemoryExtraction:

    prompt = f"""
{MEMORY_PROMPT}

PATIENT MESSAGE:
{redacted_text}
"""

    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": MemoryExtraction.model_json_schema(),
        },
    )

    return MemoryExtraction.model_validate_json(
        interaction.output_text
    )