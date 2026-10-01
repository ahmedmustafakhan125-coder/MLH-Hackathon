"""OWNER: Part 3 (UI). Spec: gui.md section 2. Working baseline - Part 3 may polish it, keep the flags."""
import argparse
import os
import sys

from .config import DEFAULT_HEAVY, DEFAULT_TINY


def main(argv=None):
    try:
        sys.stdout.reconfigure(errors="replace")     # Windows console + Unicode model output
    except Exception:
        pass
    p = argparse.ArgumentParser(prog="squeeze", description="Run the best open models your hardware can handle.")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup", help="Profile, fit and tune this machine")
    s.add_argument("--heavy", default=DEFAULT_HEAVY)
    s.add_argument("--tiny", default=DEFAULT_TINY)
    s.add_argument("--cpu-only", action="store_true")
    s.add_argument("--no-tune", action="store_true")
    r = sub.add_parser("run", help="Run a task in private mode")
    r.add_argument("task")
    r.add_argument("--online", action="store_true")
    r.add_argument("--cpu-only", action="store_true")
    r.add_argument("--simulate-pressure-at", type=int)
    r.add_argument("--min-free-gb", type=float)
    d = sub.add_parser("dashboard", help="Open the local web dashboard (127.0.0.1 only)")
    d.add_argument("--port", type=int, default=8765, help="Port on 127.0.0.1 (default 8765)")
    d.add_argument("--no-browser", action="store_true", help="Don't open a browser tab")
    a = p.parse_args(argv)
    if getattr(a, "cpu_only", False):
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    if a.cmd == "setup":
        from .bootstrap import run_setup
        run_setup(a.heavy, a.tiny, a.cpu_only, a.no_tune)
    elif a.cmd == "dashboard":
        from .dashboard import serve
        serve(port=a.port, open_browser=not a.no_browser)
    else:
        from .pipeline import run_task
        run_task(a.task, a.cpu_only, a.online, a.simulate_pressure_at, a.min_free_gb)
