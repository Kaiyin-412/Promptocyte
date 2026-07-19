"""Use the guard before invoking any LangChain chain."""
from promptocyte import SecurityGuard

guard = SecurityGuard("config.yaml")
def guarded_invoke(chain, user_input: str):
    result = guard.analyze(user_input)
    if result["decision"] == "BLOCK":
        return {"error": "Unsafe prompt", "security": result}
    return chain.invoke({"input": user_input})
