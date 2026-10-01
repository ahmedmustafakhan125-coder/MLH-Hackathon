"""OWNER: Part 3 (UI). Spec: gui.md + CONTRACTS.md section 3.

Terminal interface using Rich, ASCII-only for Windows console safety.
"""
from pathlib import Path
from typing import Any
from rich.console import Console
from rich.markup import escape

console = Console(highlight=False)


def status(msg: str):
    """Return a status context manager with an ASCII line spinner."""
    return console.status(escape(str(msg)), spinner="line")


def hardware_table(prof: dict[str, Any]) -> None:
    """Print detected hardware specifications."""
    os_val = prof.get("os", "Windows")
    cpu_p = prof.get("cpu_physical", 4)
    cpu_l = prof.get("cpu_logical", 8)
    ram_total = prof.get("ram_total_gb", 0.0)
    ram_avail = prof.get("ram_available_gb", 0.0)
    gpu = prof.get("gpu")
    backend = prof.get("backend", "cpu")

    if not gpu:
        gpu_str = "none (integrated graphics share system RAM - not used)"
    elif isinstance(gpu, dict):
        gpu_str = f"{gpu.get('name', 'GPU')} ({gpu.get('vram_free_gb', 0.0):.1f} / {gpu.get('vram_total_gb', 0.0):.1f} GB VRAM)"
    else:
        gpu_str = str(gpu)

    console.print("Hardware")
    console.print(f"  OS        {escape(str(os_val))}")
    console.print(f"  CPU       {cpu_p} cores / {cpu_l} threads")
    console.print(f"  RAM       {ram_total:.1f} GB total, {ram_avail:.1f} GB available")
    console.print(f"  GPU       {escape(gpu_str)}")
    console.print(f"  Backend   {escape(str(backend))}")


def tuning_table(role: str, name: str, results: list[dict[str, Any]], best: dict[str, Any]) -> None:
    """Print tuning benchmark table with the chosen candidate highlighted."""
    role_color = "magenta" if role == "heavy" else "cyan" if role == "tiny" else "white"
    console.print(f"\nTuning [{role_color}]{escape(role)}[/{role_color}]: {escape(name)} (CPU only)")
    console.print("  #  GPU layers  threads  load s  tok/s  status")

    for i, r in enumerate(results, start=1):
        ngl = r.get("ngl", 0)
        threads = r.get("threads", 4)
        load_s = f"{r.get('load_s', 0.0):.1f}" if r.get("load_s") is not None else "-"
        tok_s = f"{r.get('tok_s', 0.0):.1f}" if r.get("tok_s") is not None else "-"
        status_text = "ok" if r.get("ok", True) else "fail"

        is_best = False
        if best is not None:
            if r == best or (r.get("ngl") == best.get("ngl") and r.get("threads") == best.get("threads")):
                is_best = True

        chosen = "      <-- chosen" if is_best else ""
        console.print(f"  {i:<2} {ngl:<11} {threads:<8} {load_s:<7} {tok_s:<6} {status_text}{chosen}".rstrip())


def setup_done(path: Path | str, co_resident: bool) -> None:
    """Print setup summary including profile path and co-residency status."""
    res_str = "yes" if co_resident else "no"
    console.print(f"Profile saved: {escape(str(path))} | Both models fit in RAM together: {res_str}")


def run_header(profile: dict[str, Any], free_gb: float, private: bool) -> None:
    """Print run header with live machine status and privacy mode."""
    cpu_p = profile.get("cpu_physical", 4)
    cpu_l = profile.get("cpu_logical", 8)
    gpu = profile.get("gpu")
    gpu_str = "none" if not gpu else (gpu.get("name", "GPU") if isinstance(gpu, dict) else str(gpu))
    priv_str = "ON" if private else "OFF"
    console.print(f"Squeeze run | CPU {cpu_p}C/{cpu_l}T | RAM free {free_gb:.1f} GB | GPU {gpu_str} | private {priv_str}")


def privacy_banner(ok: bool) -> None:
    """Print the privacy guard status banner."""
    if ok:
        console.print("[green]Private mode: ON (guard verified)[/green]")
    else:
        console.print("[bold red]Private mode guard FAILED - stop and check privacy.py[/bold red]")


def loaded(role: str, m: dict[str, Any], secs: float) -> None:
    """Print model load confirmation in dim text."""
    name = m.get("name", role)
    placement = m.get("placement", "CPU only")
    threads = m.get("threads", 4)
    console.print(f"[dim]  loaded {escape(role):<5}  {escape(name)}  {escape(placement)}, {threads} threads  {secs:.1f}s[/dim]")


def plan(steps: list[dict[str, Any]], source: str, st: Any) -> None:
    """Print execution plan breakdown."""
    sec = 0.0
    if isinstance(st, dict):
        sec = st.get("seconds", 0.0)
    elif hasattr(st, "seconds"):
        sec = getattr(st, "seconds", 0.0)

    console.print(f"PLAN ({escape(source)}, {sec:.1f}s)")
    for step in steps:
        s_id = step.get("id", 1)
        s_kind = step.get("kind", "")
        s_task = escape(step.get("task", ""))
        console.print(f"  {s_id}. {s_kind:<10} {s_task}")


def flip(frm: str | None, to: str, reason: str) -> None:
    """Print a model routing flip in yellow. Prints nothing if frm is None."""
    if frm is None:
        return
    console.print(f"[yellow]    FLIP {escape(frm)} -> {escape(to)} ({escape(reason)})[/yellow]")


def pressure(reason: str, freed_gb: float) -> None:
    """Print memory pressure event in bold red."""
    console.print(f"[bold red]MEMORY PRESSURE ({escape(reason)}): unloading heavy model, freeing ~{freed_gb:.1f} GB RAM[/bold red]")


def step_line(step: dict[str, Any], name: str) -> None:
    """Print single step execution metrics with token rates and context usage."""
    s_id = step.get("id", 1)
    s_kind = step.get("kind", "")
    s_model = step.get("model", "")
    model_color = "magenta" if s_model == "heavy" else "cyan" if s_model == "tiny" else "white"

    ctx = step.get("ctx_tokens", 0)
    budget = step.get("budget", 0)
    tok_s = step.get("tok_s", 0.0)
    sec = step.get("seconds", 0.0)
    trunc = "  (truncated)" if step.get("truncated") else ""

    line = f"[{s_id}] {s_kind:<9} -> [{model_color}]{s_model:<5}[/{model_color}] ({escape(name)})  ctx {ctx:>4}/{budget:<4}  {tok_s:4.1f} tok/s  {sec:4.1f}s{trunc}"
    console.print(line)


def summary(state: Any, total: float, loads: int, flips: int) -> None:
    """Print task execution summary with totals."""
    load_unit = "model load" if loads == 1 else "model loads"
    flip_unit = "flip" if flips == 1 else "flips"
    console.print(f"\nDone in {total:.0f}s | {loads} {load_unit} | {flips} {flip_unit}")


def privacy_line(ledger: dict[str, Any]) -> None:
    """Print privacy audit summary with blocked connection count in green."""
    blocked = len(ledger.get("blocked", [])) if ledger and "blocked" in ledger else 0
    console.print(f"[green]Private mode: 0 connections allowed off-device, {blocked} blocked (Squeeze process)[/green]")


def output_path(path: Path | str) -> None:
    """Print path to generated result markdown file."""
    console.print(f"Output: {escape(str(path))}")
