"""FakeLlamaServer: a drop-in for squeeze.server.LlamaServer with no process and no network."""
import json

from squeeze.context import SYSTEM
from squeeze.pipeline import PLAN_SYSTEM

DEFAULT_PLAN = [("code", "Write validate_email"), ("test", "Write pytest tests"), ("docs", "Write short usage docs")]
_KIND_BY_SYSTEM = {PLAN_SYSTEM: "plan", **{text: kind for kind, text in SYSTEM.items()}}
CANNED = {
    "code": "```python\ndef validate_email(s):\n    return '@' in s and '.' in s.split('@')[-1]\n```\nNotes: simple check.",
    "test": "```python\ndef test_ok():\n    assert validate_email('a@b.co')\n```",
    "docs": "validate_email(s) returns True for plausible addresses.\n\nExample: validate_email('a@b.co')",
    "summarize": "Built validate_email with pytest tests and short usage docs, ready to run.",
}


def make_fake_server(plan=DEFAULT_PLAN, bad_plan=False, tiny_empty=False, fail_on_kind=None):
    """Return (FakeClass, log). `log` is a shared list of events:
    ("start", role) | ("stop", role) | ("chat", role, kind, max_tokens, messages).

    bad_plan      planner returns prose instead of JSON (hits the fallback plan)
    tiny_empty    the tiny model answers with 2 characters (hits escalation)
    fail_on_kind  chat() raises RuntimeError on a step of this kind (hits the `finally` block)
    """
    log = []

    class FakeLlamaServer:
        def __init__(self, role, model_path, port, ngl, ctx, threads, cpu_only=False):
            self.role, self.model_path, self.port = role, model_path, port
            self.ngl, self.ctx, self.threads, self.cpu_only = ngl, ctx, threads, cpu_only
            self.load_seconds = 0.0
            self.running = False

        def start(self, timeout=180):
            self.running = True
            self.load_seconds = 0.01
            log.append(("start", self.role))

        def stop(self):
            self.running = False
            log.append(("stop", self.role))

        def chat(self, messages, max_tokens):
            assert self.running, "chat() on a server that is not running"
            kind = _KIND_BY_SYSTEM[messages[0]["content"]]
            log.append(("chat", self.role, kind, max_tokens, messages))
            if kind == fail_on_kind:
                raise RuntimeError(f"boom on {kind}")
            if kind == "plan":
                text = ("Sure! First do the thing, then the other thing." if bad_plan
                        else json.dumps([{"kind": k, "task": t} for k, t in plan]))
            elif self.role == "tiny" and tiny_empty:
                text = "ok"
            else:
                text = CANNED[kind]
            stats = {"tok_s": 20.0, "completion_tokens": len(text) // 4 + 1,
                     "prompt_tokens": sum(len(m["content"]) for m in messages) // 4, "seconds": 0.01}
            return text, stats

    return FakeLlamaServer, log
