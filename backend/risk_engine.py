"""Compatibility export for deterministic risk scoring."""
from app.risk_engine import RiskDecision, calculate

__all__ = ["RiskDecision", "calculate"]
