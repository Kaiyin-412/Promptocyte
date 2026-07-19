"""Strict local prompt-security pipeline: regex first, ML second, policy last."""
from functools import lru_cache
from pathlib import Path
import sys

from .config import settings
from .normalization_engine import normalize_prompt
from .risk_engine import calculate
from .schemas import AnalyzeResponse
from .security_engine.regex_detector import detect


@lru_cache(maxsize=1)
def classifier():
    project_root = str(Path(__file__).resolve().parents[2])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from ml.inference import LocalSecurityClassifier
    model_path = Path(settings.ml_model_path)
    if not model_path.is_absolute():
        model_path = Path(__file__).resolve().parents[2] / model_path
    return LocalSecurityClassifier(str(model_path))


def analyze_prompt(prompt: str) -> AnalyzeResponse:
    """No LLM/API security classification: known attacks stop at regex, remaining text uses local ML."""
    normalization = normalize_prompt(prompt)
    regex_result = detect(prompt, normalization)
    if regex_result.detected:
        risk = calculate(regex_result.category, regex_result.confidence, regex_result.source)
        return AnalyzeResponse(
            original_prompt=prompt, normalized_prompt=normalization.normalized_prompt,
            transformation_detected=normalization.transformation_detected, transformations=normalization.transformations,
            risk_score=risk.score, category=regex_result.category, severity=risk.severity,
            decision=risk.decision, confidence=regex_result.confidence, source="regex",
            explanation=f"Known {regex_result.category.replace('_', ' ')} indicator matched by the fast security rules.",
        )

    prediction = classifier().predict(normalization.normalized_prompt)
    risk = calculate(prediction.category, prediction.confidence, prediction.source)
    availability_note = "local DistilBERT classifier" if prediction.model_loaded else "local ML bootstrap fallback (train the DistilBERT model for semantic coverage)"
    return AnalyzeResponse(
        original_prompt=prompt, normalized_prompt=normalization.normalized_prompt,
        transformation_detected=normalization.transformation_detected, transformations=normalization.transformations,
        risk_score=risk.score, category=prediction.category, severity=risk.severity,
        decision=risk.decision, confidence=prediction.confidence, source="ml",
        explanation=f"Classified by {availability_note}; no known regex attack pattern matched.",
    )
