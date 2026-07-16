"""Regex-first detector for clear, known prompt-security attacks."""
from dataclasses import dataclass
import re

from ..normalization_engine import NormalizationResult, normalize_prompt


@dataclass(frozen=True)
class RegexDetection:
    detected: bool
    category: str = "benign"
    confidence: float = 0.0
    source: str = "regex"
    matched_pattern: str | None = None
    normalized: bool = False


PATTERNS: dict[str, tuple[str, ...]] = {
    "prompt_injection": (
        r"\bignore (all |any |the )?(previous|prior|above) instructions?\b",
        r"\bforget (your |the )?(rules|instructions)\b",
        r"\bdisregard (your |the )?(policy|policies|rules|instructions)\b",
        r"\b(override|replace) (the )?(system|previous|prior) (rules|instructions)\b",
        r"\bfollow my instructions instead\b",
    ),
    "system_prompt_extraction": (
        r"\b(reveal|show|print|repeat) (your |the )?(system prompt|hidden instructions|system message)\b",
        r"\b(print|show|tell me) (your |the )?configuration\b",
        r"\bwhat (are|is) (your |the )?(hidden|system) instructions\b",
    ),
    "jailbreak": (
        r"\bDAN\b",
        r"\bdeveloper mode\b",
        r"\b(unrestricted|uncensored) AI\b",
        r"\b(remove|bypass) (your |the )?(limitations|safety|guardrails|restrictions)\b",
    ),
    "data_exfiltration": (
        r"\b(export|exfiltrate|dump) (confidential|private|customer|user) data\b",
        r"\b(show|give me|reveal) (private|confidential|sensitive) (information|data)\b",
    ),
    "tool_abuse": (
        r"\bperform unauthorized actions?\b",
        r"\bexecute dangerous operations?\b",
        r"\b(delete|wipe) (all |the )?(files|database|records)\b",
        r"\brm\s+-rf\b",
    ),
}


def detect(prompt: str, normalization: NormalizationResult | None = None) -> RegexDetection:
    """Return on the first high-confidence known attack; no network or model call."""
    normalization = normalization or normalize_prompt(prompt)
    for category, patterns in PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalization.normalized_prompt, flags=re.IGNORECASE):
                return RegexDetection(True, category, 0.95, "regex", pattern, normalization.transformation_detected)
    return RegexDetection(False, normalized=normalization.transformation_detected)
