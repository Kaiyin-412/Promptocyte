"""Compatibility export for the regex-first security engine."""
from app.security_engine.regex_detector import RegexDetection, detect

__all__ = ["RegexDetection", "detect"]
