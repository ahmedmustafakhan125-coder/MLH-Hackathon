import inspect

import pytest
from rich.console import Console

from squeeze import ui
from squeeze.context import TaskState

PROF = {"os": "Windows", "machine": "AMD64", "cpu_physical": 4, "cpu_logical": 8, "ram_total_gb": 15.8,
        "ram_available_gb": 9.2, "gpu": None, "backend": "cpu"}
HEAVY = {"key": "qwen3-1.7b", "name": "Qwen3-1.7B", "ngl": 0, "ctx": 4096, "threads": 4, "ram_gb": 1.6, "tok_s": 19.4}


def _step(i, kind, model, used, budget, tok_s, secs, truncated=False):
    return {"id": i, "kind": kind, "task": "t", "status": "done", "model": model, "output": "x",
            "ctx_tokens": used, "budget": budget, "truncated": truncated, "tok_s": tok_s, "seconds": secs}


@pytest.fixture
def rec(monkeypatch):
    """Record terminal output and sink events."""
    console = Console(record=True, width=140, force_terminal=False, color_system=None)
    monkeypatch.setattr(ui, "console", console)
    events = []
    ui.set_sink(events.append)
    yield console, events
    ui.set_sink(None)


def _call_everything(tmp_path):
    state = TaskState("g")
    state.steps = [_step(1, "code", "heavy", 214, 3340, 19.2, 23.8),
                   {"id": 2, "kind": "docs", "task": "d", "status": "pending", "model": None, "output": ""}]
    with ui.status("Step 1 (code) on heavy"):
        pass
    ui.hardware_table(PROF)
    ui.tuning_table("heavy", "Qwen3-1.7B", [{"ngl": 0, "threads": 4, "tok_s": 19.4, "load_s": 2.3, "ok": True},
                                            {"ngl": 0, "threads": 8, "tok_s": 0, "ok": False, "error": "boom"}],
                    {"ngl": 0, "threads": 4, "tok_s": 19.4, "load_s": 2.3, "ok": True})
    ui.setup_done(tmp_path / "profile-cpu.json", True)
    ui.run_header(PROF, 9.04, True)
    ui.privacy_banner(True)
    ui.loaded("heavy", HEAVY, 2.06)
    ui.plan(state.steps, "fallback", {"seconds": 8.7, "tok_s": 19.4})
    ui.flip("heavy", "tiny", "memory pressure")
    ui.pressure("simulated", 1.6)
    ui.step_line(state.steps[0], "Qwen3-1.7B")
    ui.summary(state, 61.2, 2, 1)
    ui.privacy_line({"enabled": True, "blocked": ["example.com"]})
    ui.output_path(tmp_path / "result.md")


def test_every_contract_function_prints_ascii_and_emits(rec, tmp_path):
    console, events = rec
    _call_everything(tmp_path)
    text = console.export_text()
    assert text.isascii(), [c for c in text if not c.isascii()]
    types = [e["type"] for e in events]
    for t in ("status", "hardware", "tuning", "setup_done", "run_header", "privacy_banner", "loaded", "plan",
              "flip", "pressure", "step", "summary", "privacy_line", "output_path"):
        assert t in types, t
    assert "<-- chosen" in text and "FAILED boom" in text and "not run" in text


def test_lines_match_the_gui_mockup():
    assert ui.fmt_step(_step(1, "code", "heavy", 214, 3340, 19.2, 23.8), "Qwen3-1.7B") == \
        "[1] code      -> heavy (Qwen3-1.7B)  ctx  214/3340  19.2 tok/s  23.8s"
    assert ui.fmt_step(_step(3, "docs", "tiny", 1004, 1024, 42.2, 6.1, True), "Qwen3-0.6B") == \
        "[3] docs      -> tiny  (Qwen3-0.6B)  ctx 1004/1024  42.2 tok/s   6.1s  (truncated)"
    assert ui.fmt_run_header(PROF, 9.0, True) == "Squeeze run | CPU 4C/8T | RAM free 9.0 GB | GPU none | private ON"
    assert ui.fmt_loaded("tiny", dict(HEAVY, name="Qwen3-0.6B"), 0.9) == "  loaded tiny   Qwen3-0.6B  CPU only, 4 threads  0.9s"
    assert ui.fmt_pressure("simulated", 1.6) == "MEMORY PRESSURE (simulated): unloading heavy model, freeing ~1.6 GB RAM"
    assert ui.fmt_flip("heavy", "tiny", "step type 'docs'") == "    FLIP heavy -> tiny (step type 'docs')"
    assert ui.fmt_plan_title("model", {"seconds": 8.7}) == "PLAN (heavy, 8.7s)"
    assert ui.fmt_plan_title("fallback", {"seconds": 8.7}) == "PLAN (heavy, 8.7s, fallback)"
    assert ui.fmt_summary(61.2, 2, 1) == "Done in 61s | 2 model loads | 1 flip"
    assert ui.fmt_summary(58, 1, 2) == "Done in 58s | 1 model load | 2 flips"
    assert ui.fmt_privacy_line({"blocked": []}) == "Private mode: 0 connections allowed off-device, 0 blocked (Squeeze process)"


def test_model_text_with_markup_is_printed_literally(rec):
    console, _ = rec
    steps = [{"id": 1, "kind": "code", "task": "print [bold]x[/] and [red", "status": "pending"}]
    ui.plan(steps, "model", {"seconds": 1.0})                   # would raise MarkupError without escape()
    assert "print [bold]x[/] and [red" in console.export_text()


def test_flip_from_none_prints_nothing(rec):
    console, events = rec
    ui.flip(None, "heavy", "start")
    assert console.export_text() == "" and events == []


def test_status_emits_start_and_end_even_on_error(rec):
    _, events = rec
    with pytest.raises(RuntimeError):
        with ui.status("Loading heavy model"):
            raise RuntimeError("x")
    assert [(e["type"], e["state"]) for e in events] == [("status", "start"), ("status", "end")]


def test_no_sink_means_no_events(monkeypatch):
    monkeypatch.setattr(ui, "console", Console(record=True, force_terminal=False))
    seen = []
    ui.set_sink(seen.append)
    ui.set_sink(None)
    ui.pressure("simulated", 1.6)
    assert seen == []


def test_tuning_table_without_results(rec):
    console, events = rec
    ui.tuning_table("tiny", "Qwen3-0.6B", [], {"ngl": 0, "threads": 4, "tok_s": None})
    assert "skipped" in console.export_text() and events[0]["results"] == []


def test_signatures_match_contract():
    expected = {"status": 1, "hardware_table": 1, "tuning_table": 4, "setup_done": 2, "run_header": 3,
                "privacy_banner": 1, "loaded": 3, "plan": 3, "flip": 3, "pressure": 2, "step_line": 2,
                "summary": 4, "privacy_line": 1, "output_path": 1}
    for name, n in expected.items():
        assert len(inspect.signature(getattr(ui, name)).parameters) == n, name
