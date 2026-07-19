from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prompt: Mapped[str] = mapped_column(Text)
    normalized_prompt: Mapped[str] = mapped_column(Text, default="")
    transformations: Mapped[str] = mapped_column(Text, default="[]")
    risk_score: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16))
    decision: Mapped[str] = mapped_column(String(16))
    explanation: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[int] = mapped_column(Integer)  # Stored as confidence * 1000.
    source: Mapped[str] = mapped_column(String(16), default="regex")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
