from dataclasses import dataclass


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