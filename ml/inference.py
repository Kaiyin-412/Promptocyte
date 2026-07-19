"""Local DistilBERT inference with bounded token-occlusion explanations."""
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

LABELS = ["benign", "prompt_injection", "jailbreak", "system_prompt_extraction", "data_exfiltration", "tool_abuse"]
MAX_EXPLANATION_TOKENS = 12


@dataclass(frozen=True)
class Prediction:
    category: str
    confidence: float
    source: str = "ml"
    model_loaded: bool = False
    explanation: str = ""
    evidence: tuple[str, ...] = ()


class LocalSecurityClassifier:
    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        self._pipeline: Any | None = None
        self._load_error: str | None = None

    @staticmethod
    def _label(label: str) -> str:
        label = label.lower()
        return LABELS[int(label.split("_")[1])] if label.startswith("label_") else label

    def _load(self) -> None:
        if self._pipeline is not None or self._load_error is not None:
            return
        if not (self.model_path / "config.json").exists():
            self._load_error = "Model not trained"
            return
        try:
            from transformers import pipeline
            self._pipeline = pipeline("text-classification", model=str(self.model_path), tokenizer=str(self.model_path), device=-1)
        except Exception as exc:
            self._load_error = str(exc)

    def _scores(self, text: str) -> dict[str, float]:
        output = self._pipeline(text, truncation=True, max_length=256, top_k=None)
        rows = output[0] if output and isinstance(output[0], list) else output
        return {self._label(item["label"]): float(item["score"]) for item in rows}

    def _evidence(self, text: str, category: str, baseline: float) -> tuple[str, ...]:
        tokens = list(dict.fromkeys(re.findall(r"\b[\w'-]+\b", text)))[:MAX_EXPLANATION_TOKENS]
        impact: list[tuple[str, float]] = []
        for token in tokens:
            ablated = re.sub(rf"\b{re.escape(token)}\b", "", text, flags=re.IGNORECASE)
            impact.append((token, baseline - self._scores(ablated).get(category, 0.0)))
        return tuple(token for token, loss in sorted(impact, key=lambda item: item[1], reverse=True)[:3] if loss > 0.01)

    def predict(self, prompt: str) -> Prediction:
        self._load()
        if self._pipeline is not None:
            scores = self._scores(prompt)
            category, confidence = max(scores.items(), key=lambda item: item[1])
            evidence = self._evidence(prompt, category, confidence) if category != "benign" else ()
            explanation = f"Local DistilBERT predicted {category.replace('_', ' ')} at {confidence:.0%} confidence."
            if evidence:
                explanation += f" Most influential tokens: {', '.join(evidence)}."
            return Prediction(category, confidence, model_loaded=True, explanation=explanation, evidence=evidence)
        return Prediction("benign", 0.55, model_loaded=False, explanation="Local ML model is not trained; using the conservative bootstrap classification.")
