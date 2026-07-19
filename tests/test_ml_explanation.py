from promptocyte.ml import LocalClassifier


class FakeClassifierPipeline:
    """Local stand-in that makes 'ignore' influential for injection confidence."""
    def __call__(self, text, **_kwargs):
        injection = 0.92 if "ignore" in text.lower() else 0.12
        return [[
            {"label": "prompt_injection", "score": injection},
            {"label": "benign", "score": 1 - injection},
        ]]


def test_ml_explanation_reports_influential_tokens():
    classifier = LocalClassifier(None)
    classifier._pipeline = FakeClassifierPipeline()

    result = classifier.classify("ignore the summary")

    assert result.category == "prompt_injection"
    assert "ignore" in result.evidence
    assert "Most influential tokens: ignore" in result.explanation
