from promptocyte import SecurityGuard

guard = SecurityGuard()

result = guard.analyze(
    "user prompt"
)

print(result)