import json

import pytest
from fakes import make_fake_server

from squeeze import pipeline
from squeeze import privacy
from squeeze.config import PRESSURE_CTX_BUDGET

GOAL = "Write a Python function validate_email(s) that returns True or False, with pytest tests and short usage docs."


def _model(key, name, ram_gb):
    return {"key": key, "name": name, "path": f"C:\\models\\{name}.gguf", "ngl": 0, "ctx": 4096,
            "threads": 4, "placement": "CPU only", "ram_gb": ram_gb, "tok_s": 19.4}


def _profile(co_resident=True):
    return {"created": "2026-10-01T15:20:00",
            "profile": {"os": "Windows", "machine": "AMD64", "cpu_physical": 4, "cpu_logical": 8,
                        "ram_total_gb": 15.8, "ram_available_gb": 9.2, "gpu": None, "backend": "cpu"},
            "co_resident": co_resident,
            "models": {"heavy": _model("qwen3-1.7b", "Qwen3-1.7B", 1.6), "tiny": _model("qwen3-0.6b", "Qwen3-0.6B", 0.9)},
            "tuning": {"heavy": [], "tiny": []}}


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Temp PROFILES_DIR / OUT_DIR plus a helper to install a fake server and run the pipeline."""
    profiles, out = tmp_path / "profiles", tmp_path / "out"
    profiles.mkdir()
    monkeypatch.setattr(pipeline, "PROFILES_DIR", profiles)
    monkeypatch.setattr(pipeline, "OUT_DIR", out)

    class Env:
        def __init__(self):
            self.profiles, self.out, self.log = profiles, out, []

        def write_profile(self, name="profile-cpu.json", **kw):
            (profiles / name).write_text(json.dumps(_profile(**kw)), encoding="utf-8")

        def run(self, goal=GOAL, fake=None, **kw):
            cls, self.log = fake or make_fake_server()
            monkeypatch.setattr(pipeline, "LlamaServer", cls)
            kw.setdefault("online", True)                    # privacy guard has its own tests
            self.result = pipeline.run_task(goal, **kw)
            return self.result

        def state(self):
            return json.loads((self.result.parent / "state.json").read_text(encoding="utf-8"))

        def events(self, kind):
            return [e for e in self.log if e[0] == kind]

    e = Env()
    e.write_profile()
    return e


def _models_by_kind(state):
    return {s["kind"]: s["model"] for s in state["steps"]}


# ---------- normal run ----------

def test_normal_run_routes_flips_and_writes_files(env):
    result = env.run()
    state = env.state()
    assert result.name == "result.md" and result.exists() and (result.parent / "state.json").exists()
    assert [s["kind"] for s in state["steps"]] == ["code", "test", "docs", "summarize"]
    assert _models_by_kind(state) == {"code": "heavy", "test": "heavy", "docs": "tiny", "summarize": "tiny"}
    assert all(s["status"] == "done" and s["budget"] > 1024 and s["ctx_tokens"] <= s["budget"] for s in state["steps"])
    assert [e[1] for e in env.events("start")] == ["heavy", "tiny"]          # one load per model
    assert sorted(e[1] for e in env.events("stop")) == ["heavy", "tiny"]

    text = result.read_text(encoding="utf-8")
    assert text.startswith("# Squeeze run ") and f"Goal: {GOAL}" in text
    assert "## Step 1: code (heavy, Qwen3-1.7B)" in text and "## Step 3: docs (tiny, Qwen3-0.6B)" in text
    assert "def validate_email" in text and "def test_ok" in text


def test_plan_always_runs_on_heavy_first_with_plan_prompt(env):
    env.run()
    first = env.events("chat")[0]
    assert first[1] == "heavy" and first[2] == "plan" and first[3] == 250
    assert first[4][1] == {"role": "user", "content": GOAL}


def test_each_step_gets_a_rebuilt_packet_with_prior_outputs(env):
    env.run()
    chats = {e[2]: e for e in env.events("chat")}
    test_packet = chats["test"][4][1]["content"]
    assert "def validate_email" in test_packet                       # the tiny/heavy hand-off carries the code
    docs_packet = chats["docs"][4][1]["content"]
    assert "[x] 1. (code)" in docs_packet and "def validate_email" in docs_packet
    assert chats["code"][3] == 500 and chats["summarize"][3] == 120  # MAX_TOKENS per kind


def test_flip_count_is_reported(env, monkeypatch):
    seen = {}
    monkeypatch.setattr(pipeline.ui, "summary", lambda state, total, loads, flips: seen.update(loads=loads, flips=flips))
    env.run()
    assert seen == {"loads": 2, "flips": 1}                          # heavy -> tiny at the docs step


def test_run_returns_without_leftover_servers_even_without_co_residency(env):
    env.write_profile(co_resident=False)
    env.run()
    # tiny can only load after heavy has been stopped
    names = [(e[0], e[1]) for e in env.log if e[0] in ("start", "stop")]
    assert names.index(("stop", "heavy")) < names.index(("start", "tiny"))
    assert sorted(e[1] for e in env.events("stop")) == ["heavy", "tiny"]


# ---------- memory pressure ----------

def test_simulated_pressure_at_step_2(env):
    env.run(pressure_at=2)
    state = env.state()
    by_id = {s["id"]: s for s in state["steps"]}
    assert by_id[1]["model"] == "heavy"
    assert all(by_id[i]["model"] == "tiny" for i in (2, 3, 4))
    assert all(by_id[i]["budget"] <= PRESSURE_CTX_BUDGET for i in (2, 3, 4))
    assert by_id[1]["budget"] > PRESSURE_CTX_BUDGET
    # heavy was unloaded BEFORE the tiny model produced its first answer
    first_tiny_chat = next(i for i, e in enumerate(env.log) if e[0] == "chat" and e[1] == "tiny")
    assert env.log.index(("stop", "heavy")) < first_tiny_chat
    assert env.log.count(("stop", "heavy")) == 1                     # not stopped again at cleanup


def test_pressure_reports_reason_and_freed_memory(env, monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline.ui, "pressure", lambda reason, freed: calls.append((reason, freed)))
    flips = []
    monkeypatch.setattr(pipeline.ui, "flip", lambda frm, to, reason: flips.append((frm, to, reason)))
    env.run(pressure_at=2)
    assert calls == [("simulated", 1.6)]
    assert ("heavy", "tiny", "memory pressure") in flips


def test_min_free_gb_real_ram_path_fires_before_step_1(env):
    env.run(min_free_gb=10_000)
    state = env.state()
    assert all(s["model"] == "tiny" for s in state["steps"])
    assert all(s["budget"] <= PRESSURE_CTX_BUDGET for s in state["steps"])
    # the plan ran on heavy first, then heavy was unloaded before step 1
    assert env.events("chat")[0][1] == "heavy" and ("stop", "heavy") in [(e[0], e[1]) for e in env.log]
    assert not [e for e in env.events("chat") if e[1] == "heavy" and e[2] != "plan"]


def test_min_free_gb_zero_headroom_does_not_trigger(env):
    env.run(min_free_gb=0.001)
    assert _models_by_kind(env.state()) == {"code": "heavy", "test": "heavy", "docs": "tiny", "summarize": "tiny"}


def test_pressure_fires_only_once(env, monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline.ui, "pressure", lambda reason, freed: calls.append(reason))
    env.run(min_free_gb=10_000)
    assert len(calls) == 1


def test_truncation_shows_up_under_pressure(env):
    fake = make_fake_server(plan=[("code", "a"), ("test", "b"), ("docs", "c")])
    cls = fake[0]
    big = "x" * 8000                                                 # a long code answer from step 1
    orig_chat = cls.chat

    def chat(self, messages, max_tokens):
        text, st = orig_chat(self, messages, max_tokens)
        return (big, st) if self.role == "heavy" and "expert programmer" in messages[0]["content"] else (text, st)
    cls.chat = chat
    env.run(fake=fake, pressure_at=2)
    by_id = {s["id"]: s for s in env.state()["steps"]}
    assert by_id[2]["truncated"] is True and by_id[2]["ctx_tokens"] <= PRESSURE_CTX_BUDGET


# ---------- planner ----------

def test_invalid_plan_json_uses_fallback_and_ends_with_summarize(env):
    env.run(fake=make_fake_server(bad_plan=True))
    steps = env.state()["steps"]
    assert [s["kind"] for s in steps] == ["code", "test", "docs", "summarize"]
    assert steps[0]["task"] == GOAL and steps[-1]["kind"] == "summarize"
    assert all(s["status"] == "done" for s in steps)


def test_plan_source_is_reported(env, monkeypatch):
    seen = []
    monkeypatch.setattr(pipeline.ui, "plan", lambda steps, source, st: seen.append(source))
    env.run(fake=make_fake_server(bad_plan=True))
    env.run()
    assert seen == ["fallback", "model"]


def test_parse_plan_valid_json_with_chatter_around_it():
    text = 'Here you go:\n```json\n[{"kind":"Code","task":" Write it "},{"kind":"docs","task":"Doc it"}]\n```'
    steps, source = pipeline.parse_plan(text, "goal")
    assert source == "model"
    assert [(s["id"], s["kind"], s["task"], s["status"], s["model"], s["output"]) for s in steps] == [
        (1, "code", "Write it", "pending", None, ""), (2, "docs", "Doc it", "pending", None, ""),
        (3, "summarize", "Summarize what was built and how to use it.", "pending", None, "")]


def test_parse_plan_filters_unknown_kinds_and_empty_tasks():
    text = '[{"kind":"plan","task":"x"},{"kind":"code","task":""},{"kind":"deploy","task":"y"},"junk",{"kind":"test","task":"t"}]'
    steps, source = pipeline.parse_plan(text, "goal")
    assert source == "model" and [s["kind"] for s in steps] == ["test", "summarize"]


@pytest.mark.parametrize("text", ["", "no json here", "[not json]", '["a","b"]', "[]", '[{"kind":"deploy","task":"x"}]'])
def test_parse_plan_falls_back(text):
    steps, source = pipeline.parse_plan(text, "my goal")
    assert source == "fallback" and steps[0]["task"] == "my goal"
    assert [s["kind"] for s in steps] == ["code", "test", "docs", "summarize"]


def test_parse_plan_caps_at_four_steps_plus_summarize_and_keeps_existing_summary():
    five = json.dumps([{"kind": "code", "task": str(i)} for i in range(6)])
    steps, _ = pipeline.parse_plan(five, "g")
    assert len(steps) == 5 and steps[-1]["kind"] == "summarize" and [s["id"] for s in steps] == [1, 2, 3, 4, 5]
    ends_with_summary = json.dumps([{"kind": "code", "task": "a"}, {"kind": "summarize", "task": "s"}])
    steps, _ = pipeline.parse_plan(ends_with_summary, "g")
    assert [s["kind"] for s in steps] == ["code", "summarize"]


# ---------- escalation ----------

def test_escalation_reruns_empty_tiny_answers_on_heavy(env, monkeypatch):
    flips = []
    monkeypatch.setattr(pipeline.ui, "flip", lambda frm, to, reason: flips.append((frm, to, reason)))
    env.run(fake=make_fake_server(tiny_empty=True))
    state = env.state()
    assert all(s["model"] == "heavy" for s in state["steps"])        # docs + summarize escalated
    assert ("tiny", "heavy", "escalation: empty output") in flips
    assert "ok" not in [s["output"] for s in state["steps"]]
    docs_chats = [e for e in env.events("chat") if e[2] == "docs"]
    assert [e[1] for e in docs_chats] == ["tiny", "heavy"]           # tried tiny first, then heavy


def test_no_escalation_under_pressure(env):
    env.run(fake=make_fake_server(tiny_empty=True), pressure_at=2)
    state = env.state()
    assert all(s["model"] == "tiny" for s in state["steps"] if s["id"] >= 2)
    assert not [e for e in env.events("chat") if e[1] == "heavy" and e[2] != "plan" and e[2] != "code"]


# ---------- cleanup on failure ----------

def test_every_server_is_stopped_even_if_a_step_raises(env):
    fake = make_fake_server(plan=[("code", "a"), ("docs", "b"), ("test", "c")], fail_on_kind="test")
    with pytest.raises(RuntimeError, match="boom on test"):
        env.run(fake=fake)
    started = [e[1] for e in env.events("start")]
    assert sorted(started) == ["heavy", "tiny"]                      # both were loaded when it blew up
    assert sorted(e[1] for e in env.events("stop")) == ["heavy", "tiny"]
    out = next(env.out.iterdir())
    state = json.loads((out / "state.json").read_text(encoding="utf-8"))
    assert [s["status"] for s in state["steps"]][:2] == ["done", "done"]   # progress is not lost
    text = (out / "result.md").read_text(encoding="utf-8")
    assert "## Step 3: test (not run)" in text and "## Step 1: code (heavy, Qwen3-1.7B)" in text


def test_server_that_fails_to_start_is_stopped(env, monkeypatch):
    cls, log = make_fake_server()

    def bad_start(self, timeout=180):
        raise TimeoutError("model did not load")
    cls.start = bad_start
    monkeypatch.setattr(pipeline, "LlamaServer", cls)
    with pytest.raises(TimeoutError):
        pipeline.run_task(GOAL, online=True)
    assert [e for e in log if e[0] == "stop"] == [("stop", "heavy")]


def test_one_failing_stop_does_not_leak_the_other_server(env, monkeypatch):
    cls, log = make_fake_server()
    orig_stop = cls.stop

    def stop(self):
        orig_stop(self)
        if self.role == "heavy":
            raise OSError("could not kill")
    cls.stop = stop
    monkeypatch.setattr(pipeline, "LlamaServer", cls)
    with pytest.raises(OSError, match="could not kill"):
        pipeline.run_task(GOAL, online=True)
    assert sorted(e[1] for e in log if e[0] == "stop") == ["heavy", "tiny"]
    assert (next(env.out.iterdir()) / "result.md").exists()


# ---------- profile loading + privacy ----------

def test_missing_profile_exits_with_setup_hint(env):
    for f in env.profiles.iterdir():
        f.unlink()
    with pytest.raises(SystemExit) as e:
        env.run()
    assert "python -m squeeze setup" in str(e.value)
    assert env.log == []                                             # nothing was started


def test_profile_selection_prefers_cuda_unless_cpu_only(env):
    cuda = _profile()
    cuda["models"]["heavy"]["name"] = "CUDA-HEAVY"
    (env.profiles / "profile-cuda.json").write_text(json.dumps(cuda), encoding="utf-8")
    assert pipeline.load_profile(False)["models"]["heavy"]["name"] == "CUDA-HEAVY"
    assert pipeline.load_profile(True)["models"]["heavy"]["name"] == "Qwen3-1.7B"


def test_private_mode_is_default_and_ledger_is_reported(env, monkeypatch):
    banners, lines = [], []
    monkeypatch.setattr(pipeline.ui, "privacy_banner", lambda ok: banners.append(ok))
    monkeypatch.setattr(pipeline.ui, "privacy_line", lambda ledger: lines.append(dict(ledger)))
    env.run(online=False)
    assert banners == [True] and lines == [{"enabled": True, "blocked": []}]
    assert privacy.LEDGER["enabled"] is True


def test_online_mode_skips_the_guard(env, monkeypatch):
    banners, lines, headers = [], [], []
    monkeypatch.setattr(pipeline.ui, "privacy_banner", lambda ok: banners.append(ok))
    monkeypatch.setattr(pipeline.ui, "privacy_line", lambda ledger: lines.append(ledger))
    monkeypatch.setattr(pipeline.ui, "run_header", lambda prof, free, private: headers.append((prof["backend"], private)))
    env.run(online=True)
    assert banners == [] and lines == [] and privacy.LEDGER["enabled"] is False
    assert headers == [("cpu", False)]


def test_run_header_gets_profile_dict_and_live_free_ram(env, monkeypatch):
    seen = []
    monkeypatch.setattr(pipeline.ui, "run_header", lambda prof, free, private: seen.append((prof, free, private)))
    env.run(online=False)
    prof, free, private = seen[0]
    assert prof["cpu_physical"] == 4 and "models" not in prof        # the Profile, not the whole JSON
    assert free > 0 and private is True


def test_ui_hooks_get_the_contract_arguments(env, monkeypatch):
    got = {}
    monkeypatch.setattr(pipeline.ui, "loaded", lambda role, m, secs: got.setdefault("loaded", []).append((role, m["name"], secs)))
    monkeypatch.setattr(pipeline.ui, "step_line", lambda step, name: got.setdefault("steps", []).append((step["id"], name)))
    monkeypatch.setattr(pipeline.ui, "output_path", lambda path: got.setdefault("path", path))
    result = env.run()
    assert got["loaded"] == [("heavy", "Qwen3-1.7B", 0.01), ("tiny", "Qwen3-0.6B", 0.01)]
    assert got["steps"] == [(1, "Qwen3-1.7B"), (2, "Qwen3-1.7B"), (3, "Qwen3-0.6B"), (4, "Qwen3-0.6B")]
    assert got["path"] == result
