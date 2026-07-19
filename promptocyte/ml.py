"""Optional local HuggingFace classification with bounded token-occlusion explanations."""
from __future__ import annotations

import re
from pathlib import Path

from .detectors import Detection

LABELS = ["benign", "prompt_injection", "jailbreak", "system_prompt_extraction", "data_exfiltration", "tool_abuse"]
MAX_EXPLANATION_TOKENS = 12


class LocalClassifier:
    def __init__(self, model_path: str | None):
        self.model_path, self._pipeline = model_path, None

    @staticmethod
    def _label(label: str) -> str:
        label = label.lower()
        return LABELS[int(label.rsplit("_", 1)[1])] if label.startswith("label_") else label

    def _load(self) -> None:
        if self._pipeline is not None or not self.model_path or not (Path(self.model_path) / "config.json").exists():
            return
        try:
            from transformers import pipeline
            # This is a local model path; pipeline never invokes hosted inference.
            self._pipeline = pipeline("text-classification", model=self.model_path, tokenizer=self.model_path, device=-1)
        except Exception:
            self._pipeline = None

    def _scores(self, text: str) -> dict[str, float]:
        output = self._pipeline(text, truncation=True, max_length=256, top_k=None)
        rows = output[0] if output and isinstance(output[0], list) else output
        return {self._label(item["label"]): float(item["score"]) for item in rows}

    def _evidence(self, text: str, category: str, baseline: float) -> tuple[str, ...]:
        """Explain a prediction by measuring score loss when a token is removed.

        Occlusion is model-agnostic, fully local, and bounded to keep inference latency
        predictable. It indicates influential tokens, not causal proof.
        """
        tokens = list(dict.fromkeys(re.findall(r"\b[\w'-]+\b", text)))[:MAX_EXPLANATION_TOKENS]
        contributions: list[tuple[str, float]] = []
        for token in tokens:
            ablated = re.sub(rf"\b{re.escape(token)}\b", "", text, flags=re.IGNORECASE)
            score = self._scores(ablated).get(category, 0.0)
            contributions.append((token, baseline - score))
        return tuple(token for token, contribution in sorted(contributions, key=lambda item: item[1], reverse=True)[:3] if contribution > 0.01)

    def classify(self, normalized_text: str) -> Detection:
        self._load()
        if self._pipeline is not None:
            scores = self._scores(normalized_text)
            category, confidence = max(scores.items(), key=lambda item: item[1])
            evidence = self._evidence(normalized_text, category, confidence) if category != "benign" else ()
            explanation = (
                f"Local classifier predicted {category.replace('_', ' ')} at {confidence:.0%} confidence. "
                + (f"Most influential tokens: {', '.join(evidence)}." if evidence else "No single token had a strong positive contribution.")
            )
            return Detection(category, confidence, "ml", explanation, evidence)
        return Detection("benign", 0.55, "ml", "Local ML model is not available; using the conservative bootstrap classification.")
