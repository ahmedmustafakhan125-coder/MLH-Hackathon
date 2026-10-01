import pytest

from squeeze.router import ALLOWED_KINDS, HEAVY_KINDS, route


def test_done_when_asserts():
    assert route("code", False) == "heavy"
    assert route("docs", False) == "tiny"
    assert route("code", True) == "tiny"


@pytest.mark.parametrize("kind,normal", [
    ("plan", "heavy"), ("code", "heavy"), ("test", "heavy"), ("docs", "tiny"), ("summarize", "tiny"),
])
def test_routing_table(kind, normal):
    assert route(kind, False) == normal
    assert route(kind, True) == "tiny"          # heavy is unloaded under pressure


def test_constants():
    assert ALLOWED_KINDS == ["code", "test", "docs", "summarize"]
    assert HEAVY_KINDS == {"plan", "code", "test"}
