"""OWNER: Part 1 (Claude). Spec: context.md. Model-neutral task memory, rebuilt into a right-sized packet per model."""
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

SYSTEM: dict = {
    "code": "You are an expert programmer. Complete the current step. Output complete, runnable code "
            "in one fenced code block, then at most 2 short lines of notes.",
    "test": "Write focused pytest tests for the code from earlier steps. Output one fenced code block only.",
    "docs": "Write short Markdown docs for the code from earlier steps: what it does, how to run it, "
            "one example. Under 150 words.",
    "summarize": "Summarize what was built across all steps in under 80 words of plain prose.",
}


@dataclass
class TaskState:
    goal: str
    steps: list = field(default_factory=list)
    # each step: {id, kind, task, status, model, output, ctx_tokens, budget, truncated, tok_s, seconds}

    def done_steps(self):
        return [s for s in self.steps if s["status"] == "done"]

    def save(self, path):
        Path(path).write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def approx_tokens(s: str) -> int:
    return len(s) // 4 + 1                 # fast and close enough for budgeting


def build_packet(state, step, budget):
    system = SYSTEM[step["kind"]]
    checklist = "\n".join(
        f"[{'x' if s['status'] == 'done' else ' '}] {s['id']}. ({s['kind']}) {s['task']}"
        for s in state.steps)
    header = f"Overall goal: {state.goal}\n\nPlan:\n{checklist}"
    current = f"\n\nYour current step ({step['id']}): {step['task']}"
    used = approx_tokens(system) + approx_tokens(header) + approx_tokens(current)
    prior, truncated = [], False
    for s in reversed(state.done_steps()):              # newest output first
        chunk = f"\n\n--- Output of step {s['id']} ({s['kind']}) ---\n{s['output']}"
        cost = approx_tokens(chunk)
        if used + cost > budget:
            room = budget - used
            if room > 150:
                chunk = chunk[: (room - 15) * 4] + "\n[...truncated to fit context budget]"  # -15 leaves room for the marker
                prior.insert(0, chunk)
                used += approx_tokens(chunk)
            truncated = True
            break
        prior.insert(0, chunk)
        used += cost
    user = header + "".join(prior) + current            # chronological order
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}], used, truncated
