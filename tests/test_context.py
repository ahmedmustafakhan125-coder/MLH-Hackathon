import json

from squeeze.context import SYSTEM, TaskState, approx_tokens, build_packet


def _step(i, kind, status="done", output="out"):
    return {"id": i, "kind": kind, "task": f"task {i}", "status": status, "model": None, "output": output}


def test_truncation_done_when():
    """The one-liner from context.md: used <= 300, truncated, marker present."""
    s = TaskState("g")
    s.steps = [{"id": 1, "kind": "code", "task": "a", "status": "done", "output": "x" * 4000},
               {"id": 2, "kind": "docs", "task": "b", "status": "pending", "output": ""}]
    msgs, used, trunc = build_packet(s, s.steps[1], 300)
    assert used <= 300 and trunc is True and "[...truncated" in msgs[1]["content"]


def test_messages_shape_and_system_prompt():
    s = TaskState("build it")
    s.steps = [_step(1, "code", "pending", "")]
    msgs, used, trunc = build_packet(s, s.steps[0], 3340)
    assert [m["role"] for m in msgs] == ["system", "user"]
    assert msgs[0]["content"] == SYSTEM["code"]
    assert "Overall goal: build it" in msgs[1]["content"]
    assert "[ ] 1. (code) task 1" in msgs[1]["content"]
    assert "Your current step (1): task 1" in msgs[1]["content"]
    assert trunc is False and used == sum(approx_tokens(m["content"]) for m in msgs)


def test_prior_outputs_are_chronological_and_checked_off():
    s = TaskState("g")
    s.steps = [_step(1, "code", output="FIRST"), _step(2, "test", output="SECOND"),
               _step(3, "docs", "pending", "")]
    user = build_packet(s, s.steps[2], 3000)[0][1]["content"]
    assert user.index("FIRST") < user.index("SECOND") < user.index("Your current step")
    assert "[x] 1. (code)" in user and "[x] 2. (test)" in user and "[ ] 3. (docs)" in user


def test_newest_output_survives_when_budget_is_tight():
    s = TaskState("g")
    s.steps = [_step(1, "code", output="OLD" * 2000), _step(2, "test", output="NEW"),
               _step(3, "docs", "pending", "")]
    msgs, used, trunc = build_packet(s, s.steps[2], 400)
    user = msgs[1]["content"]
    assert "NEW" in user and "[...truncated" in user              # newest kept whole, older one cut to fit
    assert user.count("OLD") < 2000 and user.index("OLD") < user.index("NEW")   # still chronological
    assert trunc is True and used <= 400


def test_oldest_output_dropped_whole_when_no_room_to_truncate():
    s = TaskState("g")
    s.steps = [_step(1, "code", output="A" * 2000), _step(2, "test", output="B" * 2000),
               _step(3, "docs", "pending", "")]
    # budget fits the system prompt, header and one chunk with < 150 tokens of spare room
    msgs, used, trunc = build_packet(s, s.steps[2], 700)
    assert trunc is True and used <= 700
    assert "A" * 100 not in msgs[1]["content"]


def test_bigger_budget_means_bigger_packet():
    s = TaskState("g")
    s.steps = [_step(1, "code", output="x" * 6000), _step(2, "docs", "pending", "")]
    big = build_packet(s, s.steps[1], 3340)
    small = build_packet(s, s.steps[1], 1024)      # memory-pressure budget
    assert big[2] is False and small[2] is True and small[1] < big[1] and small[1] <= 1024


def test_approx_tokens():
    assert approx_tokens("") == 1 and approx_tokens("x" * 400) == 101


def test_state_save_roundtrip(tmp_path):
    s = TaskState("goal")
    s.steps = [_step(1, "code")]
    s.save(tmp_path / "state.json")
    data = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert data["goal"] == "goal" and data["steps"][0]["id"] == 1
    assert [x["id"] for x in s.done_steps()] == [1]
