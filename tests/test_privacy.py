import http.server
import os
import socket
import threading

import pytest

from squeeze import privacy as p


@pytest.mark.parametrize("host,local", [
    ("localhost", True), ("127.0.0.1", True), ("::1", True), ("127.1.2.3", True), (b"127.0.0.1", True),
    ("1.1.1.1", False), ("example.com", False), ("192.168.1.5", False), ("0.0.0.0", False), ("", False),
])
def test_is_local(host, local):
    assert p._is_local(host) is local


def test_enable_sets_flags_and_verify_passes():
    p.enable_offline()
    assert p.LEDGER["enabled"] is True
    assert os.environ["HF_HUB_OFFLINE"] == "1" and os.environ["HF_HUB_DISABLE_TELEMETRY"] == "1"
    assert p.verify() is True
    assert p.LEDGER["blocked"] == []                 # the self-test must not be counted


def test_verify_is_false_when_guard_is_missing(monkeypatch):
    """If the connect attempt is not stopped by the guard, verify() must not claim privacy."""
    def fake_connect(self, addr):                    # stands in for an unguarded network (nothing leaves the machine)
        raise OSError("network unreachable")
    monkeypatch.setattr(socket.socket, "connect", fake_connect)
    assert p.verify() is False


def test_outside_connect_is_blocked_and_ledgered():
    p.enable_offline()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with pytest.raises(PermissionError, match="blocked a connection to 8.8.8.8"):
        s.connect(("8.8.8.8", 53))
    with pytest.raises(PermissionError):
        s.connect_ex(("8.8.8.8", 53))
    s.close()
    assert p.LEDGER["blocked"] == ["8.8.8.8", "8.8.8.8"]


def test_dns_lookup_blocked_before_resolver():
    p.enable_offline()
    with pytest.raises(PermissionError):
        socket.getaddrinfo("example.com", 443)
    with pytest.raises(PermissionError):
        socket.create_connection(("example.com", 80), timeout=1)
    assert p.LEDGER["blocked"] == ["example.com", "example.com"]


def test_httpx_to_outside_world_does_not_leak():
    httpx = pytest.importorskip("httpx")
    p.enable_offline()
    with pytest.raises(httpx.HTTPError):
        httpx.get("https://example.com", timeout=3)
    assert "example.com" in p.LEDGER["blocked"]


class _Quiet(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"pong")

    def log_message(self, *a):
        pass


def test_localhost_still_works_with_guard_on():
    """llama-server lives on 127.0.0.1: by IP, by name, and through httpx with trust_env=False."""
    httpx = pytest.importorskip("httpx")
    srv = http.server.HTTPServer(("127.0.0.1", 0), _Quiet)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        p.enable_offline()
        socket.create_connection(("127.0.0.1", port), timeout=2).close()
        socket.create_connection(("localhost", port), timeout=2).close()
        with httpx.Client(trust_env=False, timeout=3) as c:
            assert c.get(f"http://127.0.0.1:{port}/").text == "pong"
        assert p.LEDGER["blocked"] == []
    finally:
        srv.shutdown()
        srv.server_close()


def test_passive_lookup_without_host_is_allowed():
    p.enable_offline()
    socket.getaddrinfo(None, 80)                     # no hostname involved
    assert p.LEDGER["blocked"] == []


@pytest.mark.skipif(getattr(socket, "AF_UNIX", None) is None, reason="no AF_UNIX on this platform")
def test_unix_sockets_are_exempt():
    p.enable_offline()
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        with pytest.raises(OSError) as e:             # missing path, but NOT blocked by the guard
            s.connect("/nonexistent/squeeze.sock")
        assert not isinstance(e.value, PermissionError) or "private mode" not in str(e.value)
    finally:
        s.close()
    assert p.LEDGER["blocked"] == []


def test_enable_twice_does_not_stack_wrappers():
    p.enable_offline()
    first = (socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo)
    p.enable_offline()
    assert (socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo) == first
    assert p.verify() is True
    assert p.LEDGER["blocked"] == []
