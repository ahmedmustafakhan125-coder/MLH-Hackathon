"""OWNER: Part 1 (Claude). Spec: router.md. STUB - replace me."""
ALLOWED_KINDS = ["code", "test", "docs", "summarize"]
HEAVY_KINDS = {"plan", "code", "test"}


def route(kind: str, pressure: bool) -> str:
    raise NotImplementedError("router.route - Part 1 (Claude)")
