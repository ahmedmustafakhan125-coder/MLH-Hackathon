"""OWNER: Part 1 (Claude). Spec: router.md. Pure function: step kind -> model role."""
ALLOWED_KINDS = ["code", "test", "docs", "summarize"]
HEAVY_KINDS = {"plan", "code", "test"}


def route(kind: str, pressure: bool) -> str:
    if pressure:
        return "tiny"                    # the heavy model is unloaded under pressure
    return "heavy" if kind in HEAVY_KINDS else "tiny"
