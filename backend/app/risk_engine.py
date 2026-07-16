"""Deterministic policy mapping from detector confidence to enforcement decision."""
from dataclasses import dataclass

from .config import settings


@dataclass(frozen=True)
class RiskDecision:
    score: int
    severity: str
    decision: str


def calculate(category: str, confidence: float, source: str) -> RiskDecision:
    if category == "benign":
        score = round((1 - confidence) * 20)
    elif source == "regex":
        score = 90
    else:
        score = round(confidence * 100)
    severity = "critical" if score >= 80 else "medium" if score >= 50 else "low"
    decision = "block" if score > settings.warn_threshold else "warn" if score > settings.allow_threshold else "allow"
    return RiskDecision(score, severity, decision)
