"""Deterministic first-layer prompt attack detection."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .normalization import NormalizedPrompt

PATTERNS: dict[str, tuple[str, ...]] = {
    "prompt_injection": (r"\bignore (all |any |the )?(previous|prior|above) instructions?\b", r"\bforget (your |the )?(rules|instructions)\b", r"\bdisregard (your |the )?(policy|policies|rules|instructions)\b", r"\b(override|replace) (the )?(system|previous|prior) (rules|instructions)\b", r"\bfollow my instructions instead\b"),
    "system_prompt_extraction": (r"\b(reveal|show|print|repeat) (your |the )?(system prompt|hidden instructions|system message)\b", r"\b(print|show|tell me) (your |the )?configuration\b"),
    "jailbreak": (r"\bDAN\b", r"\bdeveloper mode\b", r"\b(unrestricted|uncensored) AI\b", r"\b(remove|bypass) (your |the )?(limitations|safety|guardrails|restrictions)\b"),
    "data_exfiltration": (r"\b(export|exfiltrate|dump) (confidential|private|customer|user) data\b", r"\b(show|give me|reveal) (private|confidential|sensitive) (information|data)\b"),
    "tool_abuse": (r"\bperform unauthorized actions?\b", r"\bexecute dangerous operations?\b", r"\b(delete|wipe) (all |the )?(files|database|records)\b", r"\brm\s+-rf\b"),
}

@dataclass(frozen=True)
class Detection:
    category: str
    confidence: float
    source: str
    explanation: str = ""
    evidence: tuple[str, ...] = ()


def regex_detect(prompt: NormalizedPrompt) -> Detection | None:
    for category, patterns in PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, prompt.value, flags=re.IGNORECASE)
            if match:
                phrase = match.group(0)
                return Detection(category, 0.95, "regex", f"Matched known {category.replace('_', ' ')} rule: '{phrase}'.", (phrase,))
    return None
