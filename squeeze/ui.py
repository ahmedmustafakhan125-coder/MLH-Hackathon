"""OWNER: Part 3 (UI). Spec: gui.md + CONTRACTS.md section 3.

STUB: plain-print placeholders so Parts 1 and 2 can run before the real UI lands.
Part 3 replaces this whole file with the Rich version. Keep every signature.
"""
from contextlib import contextmanager


@contextmanager
def status(msg):
    print(f"- {msg}")
    yield


def hardware_table(prof): print("Hardware", prof)
def tuning_table(role, name, results, best): print(f"Tuning {role}: {name}", results, "best:", best)
def setup_done(path, co_resident): print(f"Profile saved: {path} | Both models fit in RAM together: {'yes' if co_resident else 'no'}")
def run_header(profile, free_gb, private): print(f"Squeeze run | RAM free {free_gb:.1f} GB | private {'ON' if private else 'OFF'}")
def privacy_banner(ok): print("Private mode: ON (guard verified)" if ok else "Private mode guard FAILED")
def loaded(role, m, secs): print(f"  loaded {role}  {m['name']}  {secs:.1f}s")
def plan(steps, source, st): print(f"PLAN ({source})", [(s["id"], s["kind"], s["task"]) for s in steps])
def flip(frm, to, reason): frm and print(f"    FLIP {frm} -> {to} ({reason})")
def pressure(reason, freed_gb): print(f"MEMORY PRESSURE ({reason}): freeing ~{freed_gb} GB")
def step_line(step, name): print(f"[{step['id']}] {step['kind']} -> {step['model']} ({name}) ctx {step.get('ctx_tokens')}/{step.get('budget')}")
def summary(state, total, loads, flips): print(f"Done in {total:.0f}s | {loads} model loads | {flips} flips")
def privacy_line(ledger): print(f"Private mode: 0 connections allowed off-device, {len(ledger['blocked'])} blocked")
def output_path(path): print(f"Output: {path}")
