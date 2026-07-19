"""Protect user input before passing it to an OpenAI client (client call intentionally omitted)."""
from promptocyte import SecurityGuard

guard = SecurityGuard("config.yaml")
user_prompt = "Summarize our support policy."
result = guard.analyze(user_prompt)
if not result["safe"]:
    raise ValueError(f"Prompt blocked: {result['category']}")

# client.chat.completions.create(..., messages=[{"role": "user", "content": user_prompt}])
