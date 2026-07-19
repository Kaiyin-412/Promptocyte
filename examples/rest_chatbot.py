"""Minimal generic REST handler pattern."""
from promptocyte import SecurityGuard

guard = SecurityGuard("config.yaml")
def handle_chat(payload: dict) -> dict:
    security = guard.analyze(payload["prompt"])
    if security["decision"] == "BLOCK":
        return {"status": 400, "error": "Prompt blocked", "security": security}
    # Forward only the original user prompt to the application's chosen LLM provider.
    return {"status": 200, "security": security, "reply": "Provider invocation goes here."}
