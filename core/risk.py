from dataclasses import dataclass
from .llm_risk import assess_semantic_risk
from .redaction import redact_phi

@dataclass
class RiskResult:
    level: str
    reason: str
    confidence: float


HIGH_RISK_PHRASES = {
    "crushing chest pain": "Possible cardiac emergency",
    "difficulty breathing": "Possible breathing emergency",
    "heavy bleeding": "Possible severe bleeding",
    "want to hurt myself": "Possible self-harm risk",
}


def assess_deterministic_risk(text: str) -> RiskResult:
    text_lower = text.lower()

    for phrase, reason in HIGH_RISK_PHRASES.items():
        if phrase in text_lower:
            return RiskResult(
                level="HIGH",
                reason=reason,
                confidence=1.0,
            )

    return RiskResult(
        level="PENDING",
        reason="Requires semantic clinical risk assessment",
        confidence=0.0,
    )

def assess_risk(text: str) -> RiskResult:
    """
    Full Nightingale risk pipeline.

    1. Mandatory deterministic emergency check.
    2. Redact PII.
    3. Semantic LLM risk assessment.
    """

    # First: guaranteed fail-safe
    deterministic = assess_deterministic_risk(text)

    if deterministic.level == "HIGH":
        return deterministic

    # Never send raw identifying information to the LLM
    redacted_text = redact_phi(text)

    semantic = assess_semantic_risk(redacted_text)

    return RiskResult(
        level=semantic.level,
        reason=semantic.reason,
        confidence=semantic.confidence,
    )