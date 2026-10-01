"""Shared fixtures. Part 1 owns tests/."""
import os
import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # so a bare `pytest` can import squeeze

from squeeze import privacy


@pytest.fixture(autouse=True)
def restore_network_guard():
    """The privacy guard patches `socket` globally: put everything back after every test."""
    saved = (socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo)
    env = {k: os.environ.get(k) for k in ("HF_HUB_OFFLINE", "HF_HUB_DISABLE_TELEMETRY")}
    privacy.LEDGER.update(enabled=False, blocked=[])
    yield
    socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = saved
    for k, v in env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    privacy.LEDGER.update(enabled=False, blocked=[])
