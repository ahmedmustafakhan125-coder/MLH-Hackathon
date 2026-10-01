"""OWNER: Part 3 (UI). Spec: gui.md + CONTRACTS.md section 3. All terminal output goes through here.

Rules (Windows-safe): one console, ASCII only, spinner "line", escape() every piece of user/model text.
Each function prints to the terminal AND emits a structured event to an optional sink, which is how the
web dashboard (squeeze/dashboard.py) shows the same run live. With no sink set, events cost nothing.
"""
from contextlib import contextmanager
from pathlib import Path

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from .config import ROOT

console = Console(highlight=False)
ROLE_COLOR = {"heavy": "magenta", "tiny": "cyan"}
_sink = None


def set_sink(fn) -> None:
    """Route every UI event to `fn(event_dict)` as well as the terminal. `None` turns it off."""
    global _sink
    _sink = fn


def _emit(event_type: str, /, **data) -> None:
    if _sink is not None:
        _sink({"type": event_type, **data})


def _role(role: str, width: int = 0) -> str:
    return f"[{ROLE_COLOR.get(role, 'white')}]{escape(str(role).ljust(width))}[/]"


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _rel(path) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def _gpu_text(prof: dict) -> str:
    gpu = prof.get("gpu")
    if not gpu:
        return "none (integrated graphics share system RAM - not used)"
    return f"{gpu['name']}, {gpu['vram_free_gb']} GB free of {gpu['vram_total_gb']} GB"


def _placement(ngl: int) -> str:
    return "CPU only" if not ngl else f"{ngl} layers on GPU"


# ---------- plain-text formatters (shared by the terminal and the dashboard's terminal tab) ----------

def fmt_run_header(profile, free_gb, private) -> str:
    gpu = "none" if not profile.get("gpu") else profile["gpu"]["name"]
    return (f"Squeeze run | CPU {profile['cpu_physical']}C/{profile['cpu_logical']}T | RAM free {free_gb:.1f} GB "
            f"| GPU {gpu} | private {'ON' if private else 'OFF'}")


def fmt_loaded(role, m, secs) -> str:
    return f"  loaded {role:<5}  {m['name']}  {_placement(m.get('ngl', 0))}, {m['threads']} threads  {secs:.1f}s"


def fmt_plan_title(source, st) -> str:
    return f"PLAN (heavy, {st.get('seconds', 0):.1f}s{', fallback' if source == 'fallback' else ''})"


def fmt_plan_step(s) -> str:
    return f"  {s['id']}. {s['kind']:<10} {s['task']}"


def fmt_flip(frm, to, reason) -> str:
    return f"    FLIP {frm} -> {to} ({reason})"


def fmt_pressure(reason, freed_gb) -> str:
    return f"MEMORY PRESSURE ({reason}): unloading heavy model, freeing ~{freed_gb} GB RAM"


def fmt_step(step, name) -> str:
    line = (f"[{step['id']}] {step['kind']:<9} -> {step['model']:<5} ({name})  "
            f"ctx {step.get('ctx_tokens', 0):>4}/{step.get('budget', 0)}  "
            f"{step.get('tok_s') or 0:>4.1f} tok/s  {step.get('seconds') or 0:>4.1f}s")
    return line + ("  (truncated)" if step.get("truncated") else "")


def fmt_summary(total, loads, flips) -> str:
    return f"Done in {total:.0f}s | {_plural(loads, 'model load')} | {_plural(flips, 'flip')}"


def fmt_privacy_line(ledger) -> str:
    return f"Private mode: 0 connections allowed off-device, {len(ledger['blocked'])} blocked (Squeeze process)"


# ---------- the 14 contract functions ----------

@contextmanager
def status(msg):
    _emit("status", msg=msg, state="start")
    try:
        with console.status(escape(msg), spinner="line"):
            yield
    finally:
        _emit("status", msg=msg, state="end")


def hardware_table(prof) -> None:
    t = Table(box=None, show_header=False, pad_edge=False, padding=(0, 2))
    rows = [("OS", prof["os"]),
            ("CPU", f"{prof['cpu_physical']} cores / {prof['cpu_logical']} threads"),
            ("RAM", f"{prof['ram_total_gb']} GB total, {prof['ram_available_gb']} GB available"),
            ("GPU", _gpu_text(prof)),
            ("Backend", prof["backend"])]
    for k, v in rows:
        t.add_row(f"  {k}", escape(str(v)))
    console.print("[bold]Hardware[/]")
    console.print(t)
    _emit("hardware", profile=prof, rows=rows)


def tuning_table(role, name, results, best) -> None:
    console.print(f"\n[bold]Tuning {_role(role)}: {escape(name)} ({_placement(best.get('ngl', 0))})[/]")
    if not results:
        console.print("  [dim](skipped: using the fit config)[/]")
    else:
        t = Table(box=box.ASCII, pad_edge=False)
        for col in ("#", "GPU layers", "threads", "load s", "tok/s", "status"):
            t.add_column(col)
        for i, r in enumerate(results, 1):
            chosen = r["ok"] and r.get("ngl") == best.get("ngl") and r.get("threads") == best.get("threads")
            state = "ok" if r["ok"] else "FAILED " + str(r.get("error", ""))[:40]
            t.add_row(str(i), str(r["ngl"]), str(r["threads"]),
                      f"{r['load_s']:.1f}" if r.get("load_s") is not None else "-",
                      f"{r['tok_s']:.1f}" if r.get("tok_s") else "-",
                      escape(state) + ("  [bold green]<-- chosen[/]" if chosen else ""),
                      style=None if r["ok"] else "red")
        console.print(t)
    _emit("tuning", role=role, name=name, results=results, best=best)


def setup_done(path, co_resident) -> None:
    console.print(f"[green]Profile saved: {escape(_rel(path))} | "
                  f"Both models fit in RAM together: {'yes' if co_resident else 'no'}[/]")
    _emit("setup_done", path=str(path), co_resident=co_resident)


def run_header(profile, free_gb, private) -> None:
    line = fmt_run_header(profile, free_gb, private)
    console.print(f"[bold]{escape(line)}[/]")
    _emit("run_header", profile=profile, free_gb=round(free_gb, 1), private=private, line=line)


def privacy_banner(ok) -> None:
    line = "Private mode: ON (guard verified)" if ok else "Private mode guard FAILED - stop and check privacy.py"
    console.print(f"[bold {'green' if ok else 'red'}]{line}[/]")
    _emit("privacy_banner", ok=ok, line=line)


def loaded(role, m, secs) -> None:
    line = fmt_loaded(role, m, secs)
    console.print(f"[dim]{escape(line)}[/]")
    _emit("loaded", role=role, name=m["name"], threads=m["threads"], placement=_placement(m.get("ngl", 0)),
          ram_gb=m.get("ram_gb"), secs=round(secs, 1), line=line)


def plan(steps, source, st) -> None:
    title = fmt_plan_title(source, st)
    console.print(f"[bold]{escape(title)}[/]")
    lines = [fmt_plan_step(s) for s in steps]
    for line in lines:
        console.print(escape(line))
    _emit("plan", source=source, seconds=st.get("seconds"), tok_s=st.get("tok_s"),
          steps=[{"id": s["id"], "kind": s["kind"], "task": s["task"]} for s in steps], line="\n".join([title, *lines]))


def flip(frm, to, reason) -> None:
    if frm is None:
        return
    line = fmt_flip(frm, to, reason)
    console.print(f"[yellow]{escape(line)}[/]")
    _emit("flip", frm=frm, to=to, reason=reason, line=line)


def pressure(reason, freed_gb) -> None:
    line = fmt_pressure(reason, freed_gb)
    console.print(f"[bold red]{escape(line)}[/]")
    _emit("pressure", reason=reason, freed_gb=freed_gb, line=line)


def step_line(step, name) -> None:
    line = fmt_step(step, name)
    color = ROLE_COLOR.get(step["model"], "white")
    console.print(f"[{color}]{escape(line)}[/]")
    _emit("step", id=step["id"], kind=step["kind"], task=step["task"], model=step["model"], name=name,
          ctx_tokens=step.get("ctx_tokens"), budget=step.get("budget"), truncated=bool(step.get("truncated")),
          tok_s=step.get("tok_s"), seconds=step.get("seconds"), line=line)


def summary(state, total, loads, flips) -> None:
    t = Table(box=box.ASCII, pad_edge=False)
    for col in ("step", "kind", "model", "ctx", "tok/s", "secs", "note"):
        t.add_column(col)
    for s in state.steps:
        if s["status"] != "done":
            t.add_row(str(s["id"]), s["kind"], "-", "-", "-", "-", "not run")
            continue
        t.add_row(str(s["id"]), s["kind"], _role(s["model"]), f"{s.get('ctx_tokens')}/{s.get('budget')}",
                  f"{s.get('tok_s') or 0:.1f}", f"{s.get('seconds') or 0:.1f}", "truncated" if s.get("truncated") else "")
    console.print()
    console.print(t)
    line = fmt_summary(total, loads, flips)
    console.print(f"[bold]{line}[/]")
    _emit("summary", total=round(total, 1), loads=loads, flips=flips, line=line,
          steps=[{k: s.get(k) for k in ("id", "kind", "model", "status", "ctx_tokens", "budget", "truncated",
                                         "tok_s", "seconds")} for s in state.steps])


def privacy_line(ledger) -> None:
    line = fmt_privacy_line(ledger)
    console.print(f"[green]{line}[/]")
    _emit("privacy_line", blocked=list(ledger["blocked"]), enabled=ledger["enabled"], line=line)


def output_path(path) -> None:
    line = f"Output: {_rel(path)}"
    console.print(escape(line))
    _emit("output_path", path=str(path), line=line)
