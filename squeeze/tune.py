from .server import LlamaServer
from .config import PORTS

def candidates(fit, prof):
    if fit["ngl"] > 0:                                   # NVIDIA machines only
        ngls = sorted({fit["ngl"], fit["ngl"] // 2, 0}, reverse=True)
        return [(n, prof["cpu_physical"]) for n in ngls]
    p, l = prof["cpu_physical"], prof["cpu_logical"]
    threads = []
    for t in (p, l, p - 1):                              # your laptop: e.g. 4, 8, 3
        if t >= 1 and t not in threads:
            threads.append(t)
    return [(0, t) for t in threads]

def tune_model(role, model_path, fit, prof, cpu_only):
    cands = candidates(fit, prof)
    results = []
    for ngl, threads in cands:
        srv = LlamaServer(role, model_path, PORTS[role], ngl, fit["ctx"], threads, cpu_only)
        try:
            srv.start()
            # Warm up
            srv.chat([{"role": "user", "content": "Say OK."}], 8)
            # Benchmark
            _, stats = srv.chat([{"role": "user", "content": "Explain what a hash map is in about 80 words."}], 64)
            results.append({
                "ngl": ngl, "threads": threads, "tok_s": stats["tok_s"],
                "load_s": srv.load_seconds, "ok": True
            })
        except Exception as e:
            results.append({
                "ngl": ngl, "threads": threads, "tok_s": 0, "ok": False, "error": str(e)[:200]
            })
        finally:
            srv.stop()

    successes = [r for r in results if r["ok"]]
    if not successes:
        raise SystemExit(f"Tuning failed for {role}. Check logs/{role}-{PORTS[role]}.log")
    
    best = max(successes, key=lambda x: x["tok_s"])
    return best, results
