import os
import time
import httpx
import re
import shutil
from pathlib import Path
from subprocess import Popen, STDOUT

BIN_DIR = Path("bin")
THINK_RE = re.compile(r"<think>.*?(</think>|$)", re.S)

def find_server_binary() -> str:
    env = os.environ.get("SQUEEZE_LLAMA_SERVER")
    if env:
        return env
    for name in ("llama-server.exe", "llama-server"):
        hits = sorted(BIN_DIR.rglob(name))
        if hits:
            return str(hits[0])
    found = shutil.which("llama-server")
    if found:
        return found
    raise FileNotFoundError("llama-server not found. Extract the llama.cpp CPU build into ./bin (see downloads.md)")

class LlamaServer:
    def __init__(self, role, model_path: Path, port: int, ngl: int, ctx: int, threads: int, cpu_only=False):
        self.role = role
        self.model_path = model_path
        self.port = port
        self.ngl = ngl
        self.ctx = ctx
        self.threads = threads
        self.cpu_only = cpu_only
        self.url = f"http://127.0.0.1:{port}"
        self.client = httpx.Client(trust_env=False, timeout=httpx.Timeout(600, connect=5))
        self.process = None
        self.log_file = None
        self.load_seconds = 0.0

    def start(self, timeout=180) -> None:
        try:
            res = self.client.get(f"{self.url}/health")
            if res.status_code == 200:
                raise RuntimeError(f"Port {self.port} is in use. Run: Stop-Process -Name llama-server -Force")
        except httpx.RequestError:
            pass # Not running, which is good

        cmd = [find_server_binary(), "-m", str(self.model_path),
               "--host", "127.0.0.1", "--port", str(self.port),
               "-ngl", str(self.ngl), "-c", str(self.ctx), "-t", str(self.threads), "-np", "1"]
        
        env = os.environ.copy()
        bin_dir = str(Path(find_server_binary()).parent.absolute())
        env["LD_LIBRARY_PATH"] = bin_dir + os.pathsep + env.get("LD_LIBRARY_PATH", "")
        if self.cpu_only:
            env["CUDA_VISIBLE_DEVICES"] = "-1"
            
        Path("logs").mkdir(exist_ok=True)
        self.log_file = open(f"logs/{self.role}-{self.port}.log", "w", encoding="utf-8")
        
        t0 = time.time()
        self.process = Popen(cmd, stdout=self.log_file, stderr=STDOUT, env=env)
        
        while time.time() - t0 < timeout:
            if self.process.poll() is not None:
                self.log_file.flush()
                try:
                    with open(f"logs/{self.role}-{self.port}.log", "r", encoding="utf-8") as f:
                        lines = f.readlines()[-15:]
                except Exception:
                    lines = ["Failed to read log file."]
                raise RuntimeError("llama-server exited prematurely:\n" + "".join(lines))
            
            try:
                if self.client.get(f"{self.url}/health").status_code == 200:
                    self.load_seconds = time.time() - t0
                    return
            except httpx.RequestError:
                pass
            time.sleep(0.5)
            
        self.stop()
        raise TimeoutError("llama-server failed to start within timeout.")

    def stop(self) -> None:
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(10)
            except Exception:
                self.process.kill()
            self.process = None
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        time.sleep(1)

    def chat(self, messages: list[dict], max_tokens: int) -> tuple[str, dict]:
        msgs = [dict(m) for m in messages]
        msgs[-1]["content"] += " /no_think"
        t0 = time.time()
        r = self.client.post(f"{self.url}/v1/chat/completions",
                             json={"messages": msgs, "max_tokens": max_tokens, "temperature": 0.3})
        r.raise_for_status()
        dt = time.time() - t0
        data = r.json()
        text = THINK_RE.sub("", data["choices"][0]["message"].get("content") or "").strip()
        usage = data.get("usage") or {}
        ct = usage.get("completion_tokens") or max(1, len(text) // 4)
        tok_s = (data.get("timings") or {}).get("predicted_per_second") or ct / max(dt, 1e-6)
        return text, {"tok_s": round(tok_s, 1), "completion_tokens": ct,
                      "prompt_tokens": usage.get("prompt_tokens"), "seconds": round(dt, 1)}
