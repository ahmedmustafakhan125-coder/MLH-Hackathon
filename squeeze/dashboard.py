"""OWNER: Part 3 (UI). Local web dashboard: `python -m squeeze dashboard`.

Serves squeeze/web/ on 127.0.0.1 only and runs `pipeline.run_task` in a background thread, always in
private mode. The page polls /api/events, which replays the same events squeeze.ui prints to the terminal.
The page loads nothing from the internet (system fonts, no CDN), so it works with Wi-Fi off.
"""
import json
import platform
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import psutil

from . import __version__, pipeline, privacy, ui
from .config import GB

WEB_DIR = Path(__file__).resolve().parent / "web"
STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
          "/app.css": ("app.css", "text/css; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8")}
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; "
       "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
MAX_GOAL, MAX_BODY, MAX_RESULT = 2000, 16_384, 1_000_000


class Busy(Exception):
    pass


class NotReady(Exception):
    pass


class Run:
    """One pipeline run: its options, its UI events, and how it ended."""

    def __init__(self, run_id, goal, pressure_at, min_free_gb):
        self.id, self.goal, self.pressure_at, self.min_free_gb = run_id, goal, pressure_at, min_free_gb
        self.state, self.error, self.result_path = "running", None, None
        self.started, self.events, self._lock = time.time(), [], threading.Lock()

    def add(self, event):
        with self._lock:
            self.events.append(event)

    def since(self, n):
        with self._lock:
            return self.events[n:], len(self.events)

    def info(self):
        return {"id": self.id, "state": self.state, "goal": self.goal, "error": self.error,
                "pressure_at": self.pressure_at, "min_free_gb": self.min_free_gb}


class Dashboard:
    def __init__(self, run_fn=None):
        self.run_fn = run_fn or pipeline.run_task
        self.current = None
        self._lock, self._count = threading.Lock(), 0

    def load_profile(self):
        for name in ("profile-cuda.json", "profile-cpu.json"):        # same preference as pipeline.load_profile
            path = pipeline.PROFILES_DIR / name
            if path.exists():
                try:
                    return json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    return None
        return None

    def state(self):
        cfg, vm = self.load_profile(), psutil.virtual_memory()
        return {
            "version": __version__,
            "ready": cfg is not None,
            "profile": cfg["profile"] if cfg else None,
            "co_resident": cfg.get("co_resident") if cfg else None,
            "models": cfg["models"] if cfg else None,
            "tuning": cfg.get("tuning") if cfg else None,
            "live": {"os": platform.system(), "machine": platform.machine(),
                     "cpu_physical": psutil.cpu_count(logical=False), "cpu_logical": psutil.cpu_count(),
                     "ram_total_gb": round(vm.total / GB, 1), "ram_available_gb": round(vm.available / GB, 1)},
            "privacy": {"enabled": privacy.LEDGER["enabled"], "blocked": len(privacy.LEDGER["blocked"])},
            "run": self.current.info() if self.current else None,
        }

    def start(self, goal, simulate_pressure=False, min_free_gb=None):
        with self._lock:
            if self.current and self.current.state == "running":
                raise Busy("A run is already in progress.")
            if self.load_profile() is None:
                raise NotReady("Run `python -m squeeze setup` first.")
            self._count += 1
            run = Run(f"{time.strftime('%H%M%S')}-{self._count}", goal, 2 if simulate_pressure else None, min_free_gb)
            self.current = run
        threading.Thread(target=self._work, args=(run,), daemon=True, name=f"squeeze-run-{run.id}").start()
        return run

    def _work(self, run):
        ui.set_sink(run.add)
        try:
            run.result_path = self.run_fn(run.goal, online=False, pressure_at=run.pressure_at,
                                          min_free_gb=run.min_free_gb)
        except SystemExit as e:
            run.error = str(e.code if e.code is not None else "exited")
        except Exception as e:                        # shown in the page instead of killing the server thread
            run.error = f"{type(e).__name__}: {e}"
        finally:
            ui.set_sink(None)
            run.state = "error" if run.error else "done"
            run.add({"type": "end", "state": run.state, "error": run.error})

    def result_text(self):
        run = self.current
        if not run or run.state != "done" or not run.result_path:
            return None
        path = Path(run.result_path)
        text = path.read_text(encoding="utf-8", errors="replace")[:MAX_RESULT] if path.exists() else ""
        return {"run_id": run.id, "path": str(path), "text": text}


def _hostname(value):
    value = (value or "").strip().lower()
    if value.startswith("["):                         # [::1]:8765
        return value[1:value.find("]")] if "]" in value else value
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value


def validate_run_body(body):
    """Returns (goal, simulate_pressure, min_free_gb) or raises ValueError with a message for the page."""
    if not isinstance(body, dict):
        raise ValueError("Body must be a JSON object.")
    goal = body.get("goal")
    if not isinstance(goal, str) or not goal.strip():
        raise ValueError("Enter a task goal.")
    if len(goal) > MAX_GOAL:
        raise ValueError(f"Task goal is too long (max {MAX_GOAL} characters).")
    pressure = body.get("simulate_pressure", False)
    if not isinstance(pressure, bool):
        raise ValueError("simulate_pressure must be true or false.")
    min_free = body.get("min_free_gb")
    if min_free is not None:
        if isinstance(min_free, bool) or not isinstance(min_free, (int, float)) or not 0 < min_free <= 1024:
            raise ValueError("Free-RAM trigger must be a number of GB between 0 and 1024.")
        min_free = float(min_free)
    return goal.strip(), pressure, min_free


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        server_version, sys_version = "Squeeze", ""

        def log_message(self, *args):                 # keep the terminal for the run output
            pass

        def _send(self, code, body, ctype, extra=None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, default=str).encode("utf-8"), "application/json; charset=utf-8")

        def _local_request(self):
            """Blocks DNS-rebinding and cross-site requests: only pages served from loopback may talk to us."""
            if _hostname(self.headers.get("Host")) not in LOCAL_HOSTS:
                return False
            origin = self.headers.get("Origin")
            return origin is None or urlparse(origin).hostname in LOCAL_HOSTS

        def do_GET(self):
            if not self._local_request():
                return self._json(403, {"error": "Forbidden host."})
            url = urlparse(self.path)
            if url.path in STATIC:
                name, ctype = STATIC[url.path]
                extra = {"Content-Security-Policy": CSP} if name.endswith(".html") else None
                return self._send(200, (WEB_DIR / name).read_bytes(), ctype, extra)
            if url.path == "/api/state":
                return self._json(200, app.state())
            if url.path == "/api/events":
                try:
                    since = int(parse_qs(url.query).get("since", ["0"])[0])
                    if since < 0:
                        raise ValueError
                except ValueError:
                    return self._json(400, {"error": "since must be a non-negative integer."})
                run = app.current
                if not run:
                    return self._json(200, {"run": None, "events": [], "next": 0})
                events, nxt = run.since(since)
                return self._json(200, {"run": run.info(), "events": events, "next": nxt})
            if url.path == "/api/result":
                res = app.result_text()
                return self._json(200, res) if res else self._json(404, {"error": "No finished run yet."})
            return self._json(404, {"error": "Not found."})

        do_HEAD = do_GET

        def do_POST(self):
            if not self._local_request():
                return self._json(403, {"error": "Forbidden host."})
            if urlparse(self.path).path != "/api/run":
                return self._json(404, {"error": "Not found."})
            if not (self.headers.get("Content-Type") or "").startswith("application/json"):
                return self._json(415, {"error": "Send JSON."})
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            if not 0 < length <= MAX_BODY:
                return self._json(413 if length > MAX_BODY else 400, {"error": "Bad request size."})
            try:
                goal, pressure, min_free = validate_run_body(json.loads(self.rfile.read(length)))
            except (ValueError, UnicodeDecodeError) as e:
                return self._json(400, {"error": str(e) if isinstance(e, ValueError) and str(e) else "Invalid JSON."})
            try:
                run = app.start(goal, pressure, min_free)
            except Busy as e:
                return self._json(409, {"error": str(e)})
            except NotReady as e:
                return self._json(412, {"error": str(e)})
            return self._json(202, {"run": run.info()})

    return Handler


def create_server(host="127.0.0.1", port=8765, app=None):
    if host not in LOCAL_HOSTS:
        raise ValueError("The dashboard only binds to loopback (127.0.0.1).")
    httpd = ThreadingHTTPServer((host, port), make_handler(app or Dashboard()))
    httpd.daemon_threads = True
    return httpd


def serve(host="127.0.0.1", port=8765, open_browser=True, app=None):
    httpd = create_server(host, port, app)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    ui.console.print(f"[bold]Squeeze dashboard[/] on {url}  (127.0.0.1 only, Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
