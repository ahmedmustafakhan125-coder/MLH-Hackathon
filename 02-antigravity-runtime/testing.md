# Testing Checklist

**Owner:** both · **Time:** module checks at each checkpoint; scenarios at 0:55–1:05.

**Before every timed run:** laptop plugged in, Best performance mode on, Chrome closed.

---

## 1. Module checks (each file's "Done when")

| CP | Check | File |
|---|---|---|
| 0:12 | Profiler prints `backend: cpu` with sensible core and RAM numbers | `profiler.md` |
| CP1 | `LlamaServer` starts 0.6B, chat returns text with no `<think>`, and no process is left over | `server.md` |
| CP1 | Privacy self-test: `verify True`, external call blocked, ledger has 1 entry | `privacy.md` |
| 0:22 | Router asserts pass | `router.md` |
| CP2 | Fit returns `CPU only`, `fits: True` | `fit.md` |
| CP2 | `setup` writes `profile-cpu.json` with `co_resident: true` | `tuner.md` |
| CP2 | Context truncation test passes | `context.md` |
| 0:42 | `--help` works for all commands | `gui.md` |

## 2. End-to-end scenarios
Use the fixed demo task in every run:
`Write a Python function validate_email(s) that returns True or False, with pytest tests and short usage docs.`

| # | Scenario | Command | Pass if | Required? |
|---|---|---|---|---|
| 1 | Setup | `python -m squeeze setup` | Hardware table, 2 tuning tables, profile saved | ✅ CP2 |
| 2 | Normal run | `python -m squeeze run "<task>"` | Plan shown; code and test on heavy; docs and summary on tiny; at least 1 FLIP; `result.md` written; **record the total time** | ✅ CP3 |
| 3 | Simulated pressure | `... run "<task>" --simulate-pressure-at 2` | MEMORY PRESSURE line; heavy unloaded; later steps on tiny with budget at most 1024; run finishes | ✅ |
| 4 | Real RAM trigger | `... run "<task>" --min-free-gb 50` | Pressure fires before step 1 (free RAM is always below 50 GB). Proves the real check path | ✅ |
| 5 | Airplane mode | Wi-Fi **off**, then `... run "<task>"` | Completes; final line says **0 allowed** | ✅ |
| 6 | Droplet | See `digitalocean.md` | Output captured | Optional |
| 7 | 4B upgrade | `setup --heavy qwen3-4b`, then a run | Run under about 2.5 min, or revert to 1.7B | Optional |

## 3. After every run
```powershell
Get-Process llama-server -ErrorAction SilentlyContinue    # must print nothing
```
If anything is listed: `Stop-Process -Name llama-server -Force`, then check that `pipeline.py` stops servers inside `finally`.

## 4. Test log (fill it in while testing)

| # | Time taken | Pass? | Notes |
|---|---|---|---|
| 1 | ~1m | ✅ | Hardware and tuning tables printed. `profile-cpu.json` correctly generated. |
| 2 | 48s | ✅ | Produced result.md. 2 model loads, 3 flips. Plan executed correctly across models. |
| 3 | 28s | ✅ | Pressure simulated at step 2, heavy unloaded, fallback context capped at 1024. |
| 4 | 44s | ✅ | Real RAM constraint forced pressure before step 1. Ran flawlessly on tiny model. |
| 5 | 72s | ✅ | Privacy successfully verified offline mode: 0 connections allowed off-device. |
