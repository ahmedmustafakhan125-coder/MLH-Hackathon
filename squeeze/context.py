"""OWNER: Part 1 (Claude). Spec: context.md. STUB - replace me."""
import json
from dataclasses import dataclass, field, asdict

SYSTEM: dict = {}


@dataclass
class TaskState:
    goal: str
    steps: list = field(default_factory=list)

    def done_steps(self):
        return [s for s in self.steps if s["status"] == "done"]

    def save(self, path):
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def approx_tokens(s: str) -> int:
    return len(s) // 4 + 1


def build_packet(state, step, budget):
    raise NotImplementedError("context.build_packet - Part 1 (Claude)")
