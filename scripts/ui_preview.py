"""OWNER: Part 3 (UI). Spec: gui.md section 5 + CONTRACTS.md.

Standalone UI preview rendering both `setup` and `run` mockups with fake data.
Includes a brief status spinner demonstration with time.sleep(1.5).
"""
import sys
import time
from pathlib import Path

# Add project root to sys.path so squeeze package can be imported
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import terminal_ui as ui


def preview_setup():
    prof = {
        "os": "Windows",
        "machine": "AMD64",
        "cpu_physical": 4,
        "cpu_logical": 8,
        "ram_total_gb": 15.8,
        "ram_available_gb": 9.2,
        "gpu": None,
        "backend": "cpu",
    }

    ui.hardware_table(prof)

    heavy_results = [
        {"ngl": 0, "threads": 4, "load_s": 2.3, "tok_s": 19.4, "ok": True},
        {"ngl": 0, "threads": 8, "load_s": 2.2, "tok_s": 16.8, "ok": True},
        {"ngl": 0, "threads": 3, "load_s": 2.4, "tok_s": 15.1, "ok": True},
    ]
    ui.tuning_table("heavy", "Qwen3-1.7B", heavy_results, best=heavy_results[0])

    tiny_results = [
        {"ngl": 0, "threads": 4, "load_s": 0.9, "tok_s": 42.0, "ok": True},
        {"ngl": 0, "threads": 8, "load_s": 0.9, "tok_s": 38.5, "ok": True},
        {"ngl": 0, "threads": 3, "load_s": 1.0, "tok_s": 32.1, "ok": True},
    ]
    ui.tuning_table("tiny", "Qwen3-0.6B", tiny_results, best=tiny_results[0])

    ui.setup_done(Path(r"profiles\profile-cpu.json"), co_resident=True)


def preview_run():
    prof = {
        "os": "Windows",
        "machine": "AMD64",
        "cpu_physical": 4,
        "cpu_logical": 8,
        "ram_total_gb": 15.8,
        "ram_available_gb": 9.0,
        "gpu": None,
        "backend": "cpu",
    }

    ui.privacy_banner(True)
    ui.run_header(prof, free_gb=9.0, private=True)

    heavy_cfg = {
        "key": "qwen3-1.7b",
        "name": "Qwen3-1.7B",
        "placement": "CPU only",
        "threads": 4,
    }
    ui.loaded("heavy", heavy_cfg, 2.1)

    with ui.status("Planning (heavy)"):
        time.sleep(1.5)

    steps = [
        {"id": 1, "kind": "code", "task": "Write validate_email(s) returning True or False"},
        {"id": 2, "kind": "test", "task": "Write pytest tests for validate_email"},
        {"id": 3, "kind": "docs", "task": "Write short usage docs"},
        {"id": 4, "kind": "summarize", "task": "Summarize what was built and how to use it"},
    ]
    stats_plan = {"tok_s": 19.4, "completion_tokens": 160, "prompt_tokens": 200, "seconds": 8.7}
    ui.plan(steps, "heavy", stats_plan)

    step1 = {
        "id": 1, "kind": "code", "task": steps[0]["task"], "status": "done",
        "model": "heavy", "output": "...", "ctx_tokens": 214, "budget": 3340,
        "truncated": False, "tok_s": 19.2, "seconds": 23.8
    }
    ui.step_line(step1, "Qwen3-1.7B")

    ui.pressure("simulated", 1.6)
    ui.flip("heavy", "tiny", "memory pressure")

    tiny_cfg = {
        "key": "qwen3-0.6b",
        "name": "Qwen3-0.6B",
        "placement": "CPU only",
        "threads": 4,
    }
    ui.loaded("tiny", tiny_cfg, 0.9)

    step2 = {
        "id": 2, "kind": "test", "task": steps[1]["task"], "status": "done",
        "model": "tiny", "output": "...", "ctx_tokens": 731, "budget": 1024,
        "truncated": False, "tok_s": 41.0, "seconds": 10.3
    }
    ui.step_line(step2, "Qwen3-0.6B")

    step3 = {
        "id": 3, "kind": "docs", "task": steps[2]["task"], "status": "done",
        "model": "tiny", "output": "...", "ctx_tokens": 1004, "budget": 1024,
        "truncated": True, "tok_s": 42.2, "seconds": 6.1
    }
    ui.step_line(step3, "Qwen3-0.6B")

    step4 = {
        "id": 4, "kind": "summarize", "task": steps[3]["task"], "status": "done",
        "model": "tiny", "output": "...", "ctx_tokens": 1010, "budget": 1024,
        "truncated": True, "tok_s": 43.5, "seconds": 2.9
    }
    ui.step_line(step4, "Qwen3-0.6B")

    ui.summary(None, total=61.0, loads=2, flips=1)
    ui.privacy_line({"enabled": True, "blocked": []})
    ui.output_path(Path(r"out\20261001-153012\result.md"))


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    ui.console.print("\n=== SQUEEZE UI PREVIEW: SETUP ===", style="bold underline")
    preview_setup()

    ui.console.print("\n=== SQUEEZE UI PREVIEW: RUN ===", style="bold underline")
    preview_run()


if __name__ == "__main__":
    main()
