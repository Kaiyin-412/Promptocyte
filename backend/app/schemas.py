from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12_000)

    @field_validator("prompt")
    @classmethod
    def strip_prompt(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Prompt cannot be blank")
        return value


class AnalyzeResponse(BaseModel):
    original_prompt: str
    normalized_prompt: str
    transformation_detected: bool
    transformations: list[str]
    risk_score: int = Field(ge=0, le=100)
    category: str
    severity: str
    decision: str
    explanation: str
    confidence: float = Field(ge=0, le=1)
    source: str


class HistoryItem(AnalyzeResponse):
    id: int
    prompt: str
    created_at: datetime


class StatsResponse(BaseModel):
    total_analyzed: int
    blocked: int
    warned: int
    allowed: int
    security_score: int
