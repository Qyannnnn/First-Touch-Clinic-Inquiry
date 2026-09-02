import re


def redact_phi(text: str) -> str:
    """
    Redact obvious personal identifiers before text
    is passed to the AI.
    """

    redacted = text

    # Malaysian IC
    # Examples:
    # 010101-10-1234
    # 010101101234
    redacted = re.sub(
        r"\b\d{6}-?\d{2}-?\d{4}\b",
        "[REDACTED]",
        redacted,
    )

    # Singapore NRIC / FIN
    # Examples:
    # S1234567A
    # T1234567B
    # F1234567C
    redacted = re.sub(
        r"\b[STFGM]\d{7}[A-Z]\b",
        "[REDACTED]",
        redacted,
        flags=re.IGNORECASE,
    )

    # Malaysian mobile phone numbers
    # Examples:
    # 0123456789
    # 012-3456789
    # 012 3456789
    # +60123456789
    redacted = re.sub(
        r"(?<!\d)(?:\+?60|0)1\d[-\s]?\d{7,8}\b",
        "[REDACTED]",
        redacted,
    )

    # Clear name introduction patterns
    # Examples:
    # My name is Nur Aisyah Binti Ahmad
    # This is Sarah Tan
    # You can call me Mei Ling
    # Call me Arjun Kumar A/L Muthu
    name_patterns = [
        r"\b(my name is)\s+",
        r"\b(this is)\s+",
        r"\b(you can call me)\s+",
        r"\b(call me)\s+",
    ]

    for pattern in name_patterns:
        redacted = re.sub(
            pattern
            + r"([A-Za-z][A-Za-z'’./-]*"
              r"(?:\s+(?!and\b|but\b|because\b|with\b|who\b|i\b|my\b)"
              r"[A-Za-z][A-Za-z'’./-]*){0,7})",
            lambda m: f"{m.group(1)} [REDACTED]",
            redacted,
            flags=re.IGNORECASE,
        )

    # Conservative handling for "I'm" and "I am"
    # Requires the possible name to begin with capital letters.
    # This helps avoid deleting symptoms
    redacted = re.sub(
        r"(?i:\b(i'm|i am))\s+"
        r"([A-Z][A-Za-z'’./-]*"
        r"(?:\s+(?!and\b|but\b|because\b|with\b|who\b|I\b|my\b)"
        r"[A-Z][A-Za-z'’./-]*){0,7})",
        lambda m: f"{m.group(1)} [REDACTED]",
        redacted,
    )

    return redacted