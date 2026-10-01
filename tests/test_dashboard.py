import http.client
import json
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

import pytest
from fakes import make_fake_server
from test_pipeline import GOAL, _profile

from squeeze import dashboard, pipeline


class Client:
    def __init__(self, port):
        self.port = port

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        hdrs = {"Host": f"127.0.0.1:{self.port}", **(headers or {})}
        data = body if isinstance(body, (bytes, type(None))) else json.dumps(body).encode()
        if data is not None and "Content-Type" not in hdrs:
            hdrs["Content-Type"] = "application/json"
        conn.request(method, path, body=data, headers=hdrs)
        res = conn.getresponse()
        raw = res.read()
        conn.close()
        return res.status, dict(res.getheaders()), raw

    def json(self, method, path, body=None, headers=None):
        status, hdrs, raw = self.request(method, path, body, headers)
        return status, json.loads(raw or b"{}")

    def wait_done(self, timeout=15):
        end = time.time() + timeout
        while time.time() < end:
            _, d = self.json("GET", "/api/events?since=0")
            if d["run"] and d["run"]["state"] != "running":
                return d
            time.sleep(0.05)
        raise AssertionError("run did not finish")


@pytest.fixture
def setup_dirs(tmp_path, monkeypatch):
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    monkeypatch.setattr(pipeline, "PROFILES_DIR", profiles)
    monkeypatch.setattr(pipeline, "OUT_DIR", tmp_path / "out")
    cls, log = make_fake_server()
    monkeypatch.setattr(pipeline, "LlamaServer", cls)
    return profiles, log


@pytest.fixture
def start(setup_dirs):
    servers = []

    def _start(app=None, with_profile=True):
        profiles, _ = setup_dirs
        if with_profile:
            (profiles / "profile-cpu.json").write_text(json.dumps(_profile()), encoding="utf-8")
        httpd = dashboard.create_server("127.0.0.1", 0, app or dashboard.Dashboard())
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        servers.append(httpd)
        return Client(httpd.server_address[1])

    yield _start
    for s in servers:
        s.shutdown()
        s.server_close()


# ---------- static page ----------

def test_serves_page_assets_with_security_headers(start):
    c = start()
    status, hdrs, body = c.request("GET", "/")
    assert status == 200 and hdrs["Content-Type"].startswith("text/html")
    assert "script-src 'self'" in hdrs["Content-Security-Policy"] and "frame-ancestors 'none'" in hdrs["Content-Security-Policy"]
    assert hdrs["X-Content-Type-Options"] == "nosniff"
    assert b"/app.js" in body and b"/app.css" in body
    assert c.request("GET", "/app.css")[1]["Content-Type"].startswith("text/css")
    assert c.request("GET", "/app.js")[1]["Content-Type"].startswith("text/javascript")
    assert c.request("GET", "/../squeeze/config.py")[0] == 404
    assert c.request("GET", "/nope")[0] == 404


def test_page_makes_no_external_requests():
    """Private mode: no CDN, no web fonts, no analytics. (The SVG xmlns in the favicon is a name, not a request.)"""
    for name in ("index.html", "app.css", "app.js"):
        text = (dashboard.WEB_DIR / name).read_text(encoding="utf-8")
        urls = [u for u in re.findall(r"https?://[^\s'\")]+", text) if "www.w3.org/2000/svg" not in u]
        assert urls == [], (name, urls)
        assert "@import" not in text and "fonts.googleapis" not in text


def test_app_js_never_uses_innerhtml():
    js = (dashboard.WEB_DIR / "app.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js and "eval(" not in js


# ---------- security ----------

def test_rejects_foreign_host_and_origin(start):
    c = start()
    assert c.request("GET", "/api/state", headers={"Host": "evil.example:8765"})[0] == 403        # DNS rebinding
    assert c.request("POST", "/api/run", {"goal": "x"}, headers={"Origin": "https://evil.example"})[0] == 403
    assert c.request("GET", "/", headers={"Host": "localhost:1234"})[0] == 200
    assert c.request("GET", "/", headers={"Host": "[::1]:1234"})[0] == 200


def test_only_binds_loopback():
    with pytest.raises(ValueError):
        dashboard.create_server("0.0.0.0", 0)


@pytest.mark.parametrize("body,code", [
    ({"goal": ""}, 400), ({"goal": "   "}, 400), ({"goal": "x" * 2001}, 400), ({}, 400), ([1, 2], 400),
    ({"goal": "ok", "simulate_pressure": "yes"}, 400), ({"goal": "ok", "min_free_gb": -1}, 400),
    ({"goal": "ok", "min_free_gb": "4"}, 400), ({"goal": "ok", "min_free_gb": True}, 400),
])
def test_run_input_validation(start, body, code):
    c = start()
    assert c.json("POST", "/api/run", body)[0] == code


def test_bad_content_type_json_and_since(start):
    c = start()
    assert c.request("POST", "/api/run", b'{"goal":"x"}', headers={"Content-Type": "text/plain"})[0] == 415
    assert c.request("POST", "/api/run", b"{not json")[0] == 400
    assert c.request("POST", "/api/nope", {"goal": "x"})[0] == 404
    assert c.request("GET", "/api/events?since=-1")[0] == 400
    assert c.request("GET", "/api/events?since=abc")[0] == 400


# ---------- state + runs ----------

def test_state_before_setup_and_run_refused(start):
    c = start(with_profile=False)
    status, s = c.json("GET", "/api/state")
    assert status == 200 and s["ready"] is False and s["models"] is None and s["run"] is None
    assert s["live"]["ram_total_gb"] > 0 and s["live"]["cpu_logical"] >= 1
    status, err = c.json("POST", "/api/run", {"goal": GOAL})
    assert status == 412 and "squeeze setup" in err["error"]
    assert c.json("GET", "/api/result")[0] == 404


def test_full_run_streams_ui_events_and_result(start, setup_dirs):
    c = start()
    _, s = c.json("GET", "/api/state")
    assert s["ready"] is True and s["models"]["heavy"]["name"] == "Qwen3-1.7B"
    status, r = c.json("POST", "/api/run", {"goal": GOAL, "simulate_pressure": True})
    assert status == 202 and r["run"]["pressure_at"] == 2
    d = c.wait_done()
    assert d["run"]["state"] == "done", d["run"]["error"]
    types = [e["type"] for e in d["events"]]
    for t in ("privacy_banner", "run_header", "loaded", "plan", "pressure", "flip", "step", "summary",
              "privacy_line", "output_path", "end"):
        assert t in types, t
    steps = [e for e in d["events"] if e["type"] == "step"]
    assert [e["model"] for e in steps] == ["heavy", "tiny", "tiny", "tiny"]
    assert all(e["budget"] <= 1024 for e in steps[1:])
    assert all(e.get("line") for e in d["events"] if e["type"] in ("step", "flip", "pressure", "summary"))
    status, res = c.json("GET", "/api/result")
    assert status == 200 and "def validate_email" in res["text"] and res["path"].endswith("result.md")
    _, s = c.json("GET", "/api/state")
    assert s["privacy"]["enabled"] is True and s["run"]["state"] == "done"
    _, log = setup_dirs
    assert sorted(e[1] for e in log if e[0] == "start") == sorted(e[1] for e in log if e[0] == "stop")


def test_events_since_returns_only_new_events(start):
    c = start()
    c.json("POST", "/api/run", {"goal": GOAL})
    d = c.wait_done()
    total = d["next"]
    _, tail = c.json("GET", f"/api/events?since={total - 2}")
    assert len(tail["events"]) == 2 and tail["events"][-1]["type"] == "end" and tail["next"] == total


def test_second_run_while_busy_is_409_then_allowed(start):
    gate, entered = threading.Event(), threading.Event()

    def slow_run(goal, **kw):
        entered.set()
        gate.wait(5)
        return Path("nowhere/result.md")

    c = start(app=dashboard.Dashboard(run_fn=slow_run))
    assert c.json("POST", "/api/run", {"goal": "first"})[0] == 202
    entered.wait(5)
    status, err = c.json("POST", "/api/run", {"goal": "second"})
    assert status == 409 and "already" in err["error"]
    gate.set()
    c.wait_done()
    assert c.json("POST", "/api/run", {"goal": "third"})[0] == 202
    c.wait_done()


def test_failed_run_is_reported_and_server_survives(start):
    def broken(goal, **kw):
        raise RuntimeError("llama-server exited prematurely")

    c = start(app=dashboard.Dashboard(run_fn=broken))
    c.json("POST", "/api/run", {"goal": GOAL})
    d = c.wait_done()
    assert d["run"]["state"] == "error" and "exited prematurely" in d["run"]["error"]
    assert d["events"][-1] == {"type": "end", "state": "error", "error": "RuntimeError: llama-server exited prematurely"}
    assert c.json("GET", "/api/state")[0] == 200


def test_run_options_reach_the_pipeline(start):
    seen = {}

    def spy(goal, **kw):
        seen.update(goal=goal, **kw)
        return Path("x/result.md")

    c = start(app=dashboard.Dashboard(run_fn=spy))
    c.json("POST", "/api/run", {"goal": "  build it  ", "simulate_pressure": False, "min_free_gb": 3})
    c.wait_done()
    assert seen == {"goal": "build it", "online": False, "pressure_at": None, "min_free_gb": 3.0}


# ---------- real browser smoke test (skipped when no Edge/Chrome) ----------

def _browser():
    for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
        if Path(p).exists():
            return p
    return shutil.which("chromium") or shutil.which("google-chrome")


@pytest.mark.skipif(_browser() is None, reason="no Chromium-based browser installed")
def test_page_renders_a_finished_run_in_a_real_browser(start, tmp_path):
    c = start()
    c.json("POST", "/api/run", {"goal": GOAL, "simulate_pressure": True})
    c.wait_done()
    out = subprocess.run([_browser(), "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                          f"--user-data-dir={tmp_path / 'profile'}", "--virtual-time-budget=6000", "--dump-dom",
                          f"http://127.0.0.1:{c.port}/"], capture_output=True, text=True, timeout=90,
                         encoding="utf-8", errors="replace")
    dom = out.stdout
    assert "SYS_STATUS: ONLINE" in dom                          # /api/state rendered
    assert "Qwen3-1.7B" in dom and "MEMORY PRESSURE" in dom      # events replayed into the flow
    assert "FLIP heavy" in dom and "DONE in" in dom
    assert "def validate_email" in dom                           # result.md loaded
