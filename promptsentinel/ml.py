"""Optional local HuggingFace classifier. It never calls remote inference APIs."""
from __future__ import annotations

from pathlib import Path

from .detectors import Detection

LABELS = ["benign", "prompt_injection", "jailbreak", "system_prompt_extraction", "data_exfiltration", "tool_abuse"]

class LocalClassifier:
    def __init__(self, model_path: str | None): self.model_path, self._pipeline = model_path, None
    def classify(self, normalized_text: str) -> Detection:
        if self._pipeline is None and self.model_path and (Path(self.model_path) / "config.json").exists():
            try:
                from transformers import pipeline
                self._pipeline = pipeline("text-classification", model=self.model_path, tokenizer=self.model_path, device=-1)
            except Exception: pass
        if self._pipeline is not None:
            output = self._pipeline(normalized_text, truncation=True, max_length=256)[0]
            label = output["label"].lower()
            if label.startswith("label_"): label = LABELS[int(label.rsplit("_", 1)[1])]
            return Detection(label, float(output["score"]), "ml")
        return Detection("benign", 0.55, "ml")
