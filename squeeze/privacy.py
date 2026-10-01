"""OWNER: Part 1 (Claude). Spec: privacy.md + CONTRACTS.md section 4.5.

Private mode: this Python process may only talk to loopback. Both `connect` and the DNS lookup
(`getaddrinfo`) are guarded, and every blocked attempt lands in LEDGER. This does NOT cover other
processes on the machine (see the README privacy table).
"""
import ipaddress
import os
import socket

LEDGER = {"enabled": False, "blocked": []}


def _is_local(host) -> bool:
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(str(host).split("%")[0]).is_loopback
    except ValueError:
        return False


def _block(host) -> None:
    LEDGER["blocked"].append(str(host))
    raise PermissionError(f"Squeeze private mode blocked a connection to {host}")


def _check(sock, addr):
    if getattr(socket, "AF_UNIX", None) is not None and sock.family == socket.AF_UNIX:
        return
    host = addr[0] if isinstance(addr, tuple) else addr
    if not _is_local(host):
        _block(host)


def enable_offline() -> None:
    os.environ.update(HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    LEDGER["enabled"] = True
    if getattr(socket.socket.connect, "_squeeze_guard", False):
        return                                       # already patched: don't stack wrappers
    orig, orig_ex, orig_gai = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo

    def connect(self, addr):
        _check(self, addr)
        return orig(self, addr)

    def connect_ex(self, addr):
        _check(self, addr)
        return orig_ex(self, addr)

    def getaddrinfo(host, *args, **kwargs):
        if host not in (None, "") and not _is_local(host):
            _block(host)                             # stop the lookup before it reaches the OS resolver
        return orig_gai(host, *args, **kwargs)

    for fn in (connect, connect_ex, getaddrinfo):
        fn._squeeze_guard = True
    socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = connect, connect_ex, getaddrinfo


def verify() -> bool:
    """Self-test: an outside connection must be blocked before any packet leaves."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(2)
        s.connect(("1.1.1.1", 443))
        return False                         # should never happen in private mode
    except PermissionError:
        LEDGER["blocked"].pop()              # don't count the self-test
        return True
    except OSError:
        return False
    finally:
        s.close()
