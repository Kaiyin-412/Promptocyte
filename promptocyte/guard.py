"""High-level reusable prompt security guard."""
from __future__ import annotations

from pathlib import Path

from .config import GuardConfig
from .config_loader import load_config
from .detectors import Detection, regex_detect
from .ml import LocalClassifier
from .normalization import normalize_prompt

class SecurityGuard:
    def __init__(self, config_path: str | Path | None = None, **overrides):
        config = load_config(config_path)
        # Keyword overrides retain compatibility with earlier SDK releases.
        self.config = GuardConfig(**{**config.__dict__, **{key: value for key, value in overrides.items() if value is not None}})
        self.classifier = LocalClassifier(self.config.model_path) if self.config.enable_ml else None

    def analyze(self, prompt: str) -> dict:
        normalized = normalize_prompt(prompt)
        detection = regex_detect(normalized)
        if detection is None:
            detection = self.classifier.classify(normalized.value) if self.classifier else Detection("benign", 0.55, "ml")
        score = 90 if detection.source == "regex" and detection.category != "benign" else round((1 - detection.confidence) * 20) if detection.category == "benign" else round(detection.confidence * 100)
        decision = "BLOCK" if score > self.config.warn_threshold else "WARN" if score > self.config.allow_threshold else "ALLOW"
        return {
            "safe": decision == "ALLOW", "category": detection.category, "confidence": round(detection.confidence, 4),
            "risk_score": score, "decision": decision, "detection_source": detection.source,
            "original_prompt": normalized.original, "normalized_prompt": normalized.value,
            "transformation_detected": bool(normalized.transformations), "transformations": normalized.transformations,
            "explanation": detection.explanation,
            "evidence": list(detection.evidence),
        }
