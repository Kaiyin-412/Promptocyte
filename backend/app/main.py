import json

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from .analyzer import analyze_prompt
from .database import Base, engine, get_db
from .models import AnalysisRecord
from .schemas import AnalyzeRequest, AnalyzeResponse, HistoryItem, StatsResponse

Base.metadata.create_all(bind=engine)

# Lightweight SQLite migration for local MVP upgrades.
with engine.begin() as connection:
    columns = {column["name"] for column in inspect(connection).get_columns("analysis_records")}
    if "confidence" not in columns:
        connection.execute(text("ALTER TABLE analysis_records ADD COLUMN confidence INTEGER NOT NULL DEFAULT 0"))
    if "source" not in columns:
        connection.execute(text("ALTER TABLE analysis_records ADD COLUMN source VARCHAR(16) NOT NULL DEFAULT 'regex'"))
    if "normalized_prompt" not in columns:
        connection.execute(text("ALTER TABLE analysis_records ADD COLUMN normalized_prompt TEXT NOT NULL DEFAULT ''"))
    if "transformations" not in columns:
        connection.execute(text("ALTER TABLE analysis_records ADD COLUMN transformations TEXT NOT NULL DEFAULT '[]'"))
    if "evidence" not in columns:
        connection.execute(text("ALTER TABLE analysis_records ADD COLUMN evidence TEXT NOT NULL DEFAULT '[]'"))

app = FastAPI(title="Promptocyte API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest, db: Session = Depends(get_db)):
    result = analyze_prompt(payload.prompt)
    values = result.model_dump()
    values["confidence"] = round(values["confidence"] * 1000)
    record = AnalysisRecord(
        prompt=result.original_prompt, normalized_prompt=result.normalized_prompt,
        transformations=json.dumps(result.transformations),
        risk_score=values["risk_score"], category=values["category"], severity=values["severity"],
        decision=values["decision"], explanation=values["explanation"], confidence=values["confidence"], source=values["source"],
        evidence=json.dumps(values["evidence"]),
    )
    db.add(record)
    db.commit()
    return result


@app.get("/history", response_model=list[HistoryItem])
def history(limit: int = 20, db: Session = Depends(get_db)):
    limit = min(max(limit, 1), 100)
    records = db.scalars(select(AnalysisRecord).order_by(AnalysisRecord.created_at.desc()).limit(limit)).all()
    return [HistoryItem(
        id=item.id, prompt=item.prompt, original_prompt=item.prompt, normalized_prompt=item.normalized_prompt,
        transformation_detected=bool(json.loads(item.transformations or "[]")), transformations=json.loads(item.transformations or "[]"),
        risk_score=item.risk_score, category=item.category, severity=item.severity, decision=item.decision,
        explanation=item.explanation, evidence=json.loads(item.evidence or "[]"), confidence=item.confidence / 1000, source=item.source, created_at=item.created_at,
    ) for item in records]


@app.get("/stats", response_model=StatsResponse)
def stats(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(AnalysisRecord)) or 0
    counts = dict(db.execute(select(AnalysisRecord.decision, func.count()).group_by(AnalysisRecord.decision)).all())
    # Current posture starts protected and decreases only as hostile traffic is observed.
    security_score = max(0, 100 - (counts.get("block", 0) * 3 + counts.get("warn", 0)))
    return StatsResponse(total_analyzed=total, blocked=counts.get("block", 0), warned=counts.get("warn", 0), allowed=counts.get("allow", 0), security_score=security_score)
