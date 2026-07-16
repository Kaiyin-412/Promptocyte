"""Versioned FastAPI server factory for PromptSentinel."""
from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel, Field
from .guard import SecurityGuard

class AnalyzeRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12_000)

def create_app(config_path: str | None = None) -> FastAPI:
    guard = SecurityGuard(config_path)
    app = FastAPI(title="PromptSentinel API", version="0.1.0")
    @app.get("/health")
    def health(): return {"status": "ok"}
    @app.post("/v1/security/analyze")
    def analyze(payload: AnalyzeRequest): return guard.analyze(payload.prompt)
    return app

app = create_app()
