"""Local-only DistilBERT inference with a safe fallback until a model is trained."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LABELS = ["benign", "prompt_injection", "jailbreak", "system_prompt_extraction", "data_exfiltration", "tool_abuse"]


@dataclass(frozen=True)
class Prediction:
    category: str
    confidence: float
    source: str = "ml"
    model_loaded: bool = False


class LocalSecurityClassifier:
    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        self._pipeline: Any | None = None
        self._load_error: str | None = None

    def _load(self) -> None:
        if self._pipeline is not None or self._load_error is not None:
            return
        if not (self.model_path / "config.json").exists():
            self._load_error = "Model not trained"
            return
        try:
            from transformers import pipeline
            self._pipeline = pipeline("text-classification", model=str(self.model_path), tokenizer=str(self.model_path), device=-1)
        except Exception as exc:  # Keep the firewall available if a local asset is corrupted.
            self._load_error = str(exc)

    def predict(self, prompt: str) -> Prediction:
        self._load()
        if self._pipeline is not None:
            output = self._pipeline(prompt, truncation=True, max_length=256)[0]
            label = output["label"].lower()
            if label.startswith("label_"):
                label = LABELS[int(label.split("_")[1])]
            return Prediction(label, float(output["score"]), model_loaded=True)
        # Offline bootstrap behavior: benign is conservative because regex is always the first gate.
        return Prediction("benign", 0.55, model_loaded=False)
