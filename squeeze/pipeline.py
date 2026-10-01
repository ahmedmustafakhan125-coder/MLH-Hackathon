"""OWNER: Part 1 (Claude). Spec: pipeline.md. The `run` command: plan, route, flip, survive pressure, write results."""
import json
import re
import sys
import time
from pathlib import Path

import psutil

from . import privacy, ui
from .config import CTX_MARGIN, GB, MAX_TOKENS, OUT_DIR, PORTS, PRESSURE_CTX_BUDGET, PROFILES_DIR
from .context import TaskState, build_packet
from .router import ALLOWED_KINDS, route
from .server import LlamaServer

PLAN_SYSTEM = (
    "Break the user's task into 2 to 4 steps. Each step kind must be one of: code, test, docs, summarize.\n"
    "Return ONLY a JSON array, no prose, no markdown fences.\n"
    'Example: [{"kind":"code","task":"Write the function"},{"kind":"test","task":"Write pytest tests"}]'
)


def load_profile(cpu_only: bool) -> dict:
    names = ["profile-cpu.json"] if cpu_only else ["profile-cuda.json", "profile-cpu.json"]
    for name in names:
        path = PROFILES_DIR / name
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    sys.exit("Run `python -m squeeze setup` first.")


class Runner:
    def __init__(self, cfg, cpu_only):
        self.cfg, self.cpu_only = cfg, cpu_only
        self.servers, self.loads, self.flips = {}, 0, 0
        self.last_role, self.pressure = None, False

    def ensure(self, role):                      # load the model only if needed
        if role in self.servers:
            return self.servers[role]
        if not self.cfg.get("co_resident", False):
            for r in list(self.servers):
                self.stop(r)
        m = self.cfg["models"][role]
        srv = LlamaServer(role, Path(m["path"]), PORTS[role], m["ngl"], m["ctx"], m["threads"], self.cpu_only)
        try:
            with ui.status(f"Loading {role} model ({m['name']})"):
                srv.start()
        except BaseException:
            srv.stop()                           # a half-started server must not outlive the failure
            raise
        self.loads += 1
        ui.loaded(role, m, srv.load_seconds)
        self.servers[role] = srv
        return srv

    def stop(self, role):
        srv = self.servers.pop(role, None)
        if srv:
            srv.stop()

    def stop_all(self):
        errors = []
        for r in list(self.servers):             # try every server even if one fails to stop
            try:
                self.stop(r)
            except Exception as e:
                errors.append(e)
        if errors:
            raise errors[0]

    def flip(self, frm, to, reason):
        self.flips += 1
        ui.flip(frm, to, reason)
        self.last_role = to

    def on_pressure(self, reason):
        self.pressure = True
        ui.pressure(reason, self.cfg["models"]["heavy"]["ram_gb"])
        self.stop("heavy")


def parse_plan(text, goal):
    steps, source = [], "model"
    m = re.search(r"\[.*\]", text, re.S)
    try:
        for item in json.loads(m.group(0)) if m else []:
            if isinstance(item, dict):
                kind = str(item.get("kind", "")).strip().lower()
                task = str(item.get("task", "")).strip()
                if kind in ALLOWED_KINDS and task:
                    steps.append({"kind": kind, "task": task})
    except (json.JSONDecodeError, TypeError):
        steps = []
    if not steps:
        source = "fallback"
        steps = [{"kind": "code", "task": goal},
                 {"kind": "test", "task": "Write pytest tests for the code."},
                 {"kind": "docs", "task": "Write short usage docs."}]
    steps = steps[:4]
    if steps[-1]["kind"] != "summarize":
        steps.append({"kind": "summarize", "task": "Summarize what was built and how to use it."})
    for i, s in enumerate(steps, 1):
        s.update(id=i, status="pending", model=None, output="")
    return steps, source


def run_step(runner, state, step, role):
    m = runner.cfg["models"][role]
    budget = m["ctx"] - MAX_TOKENS[step["kind"]] - CTX_MARGIN
    if runner.pressure:
        budget = min(budget, PRESSURE_CTX_BUDGET)
    msgs, used, trunc = build_packet(state, step, budget)
    with ui.status(f"Step {step['id']} ({step['kind']}) on {role}"):
        text, st = runner.ensure(role).chat(msgs, MAX_TOKENS[step["kind"]])
    return text, st, used, budget, trunc


def write_result_md(path, state, run_id, models=None):
    lines = [f"# Squeeze run {run_id}", f"Goal: {state.goal}", ""]
    for s in state.steps:
        if s["status"] == "done":
            name = (models or {}).get(s["model"], {}).get("name")
            who = f"{s['model']}, {name}" if name else str(s["model"])
            lines += [f"## Step {s['id']}: {s['kind']} ({who})", s["output"], ""]
        else:
            lines += [f"## Step {s['id']}: {s['kind']} (not run)", ""]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def run_task(goal, cpu_only=False, online=False, pressure_at=None, min_free_gb=None) -> Path:
    cfg = load_profile(cpu_only)
    if not online:
        privacy.enable_offline()
        ui.privacy_banner(privacy.verify())
    ui.run_header(cfg["profile"], psutil.virtual_memory().available / GB, not online)

    run_id = time.strftime("%Y%m%d-%H%M%S")
    out_dir = OUT_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    runner, state, t0 = Runner(cfg, cpu_only), TaskState(goal), time.time()
    try:
        # PLAN (always on heavy)
        heavy = runner.ensure("heavy")
        runner.last_role = "heavy"
        with ui.status("Planning (heavy)"):
            text, st = heavy.chat([{"role": "system", "content": PLAN_SYSTEM},
                                   {"role": "user", "content": goal}], MAX_TOKENS["plan"])
        state.steps, source = parse_plan(text, goal)
        ui.plan(state.steps, source, st)

        for step in state.steps:
            # (a) memory check, at step boundaries only
            reason = None
            if not runner.pressure:
                if pressure_at is not None and step["id"] == pressure_at:
                    reason = "simulated"
                elif min_free_gb is not None and psutil.virtual_memory().available / GB < min_free_gb:
                    reason = f"free RAM below {min_free_gb} GB"
            if reason:
                runner.on_pressure(reason)

            # (b) route + flip
            role = route(step["kind"], runner.pressure)
            if role != runner.last_role:
                runner.flip(runner.last_role, role, "memory pressure" if reason else f"step type '{step['kind']}'")

            # (c) rebuild context for THIS model, then run
            text, st, used, budget, trunc = run_step(runner, state, step, role)

            # (d) escalation: tiny gave a near-empty answer, retry on heavy
            if role == "tiny" and not runner.pressure and len(text.strip()) < 20:
                runner.flip("tiny", "heavy", "escalation: empty output")
                role = "heavy"
                text, st, used, budget, trunc = run_step(runner, state, step, role)

            step.update(status="done", model=role, output=text, ctx_tokens=used,
                        budget=budget, truncated=trunc, tok_s=st["tok_s"], seconds=st["seconds"])
            ui.step_line(step, cfg["models"][role]["name"])
    finally:
        try:
            runner.stop_all()
        finally:
            state.save(out_dir / "state.json")
            write_result_md(out_dir / "result.md", state, run_id, cfg["models"])

    ui.summary(state, time.time() - t0, runner.loads, runner.flips)
    if not online:
        ui.privacy_line(privacy.LEDGER)
    ui.output_path(out_dir / "result.md")
    return out_dir / "result.md"
