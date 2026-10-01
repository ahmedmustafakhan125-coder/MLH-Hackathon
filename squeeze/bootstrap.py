import json
import datetime
from pathlib import Path

from .profiler import profile
from .tune import tune_model
from .fit import fit_model
from .config import REGISTRY_PATH, MODELS_DIR, PROFILES_DIR, RAM_RESERVE_GB
from . import ui

def resolve_model(glob_pattern: str) -> Path:
    hits = sorted(MODELS_DIR.glob(glob_pattern))
    if hits:
        return hits[0]
    return None

def run_setup(heavy_key: str, tiny_key: str, cpu_only: bool, no_tune: bool) -> Path:
    prof = profile(cpu_only)
    ui.hardware_table(prof)

    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    heavy_entry = registry.get(heavy_key)
    tiny_entry = registry.get(tiny_key)
    
    if not heavy_entry or not tiny_entry:
        raise SystemExit(f"Keys {heavy_key} or {tiny_key} not found in models.json")

    heavy_path = resolve_model(heavy_entry["glob"])
    tiny_path = resolve_model(tiny_entry["glob"])

    if not heavy_path or not tiny_path:
        raise SystemExit("Models not found. Run the download commands from downloads.md.")

    # Heavy Model
    heavy_fit = fit_model(heavy_entry, heavy_path, prof)
    if not heavy_fit["fits"]:
        raise SystemExit("Close apps to free RAM, or use a smaller model via --heavy.")

    if no_tune:
        heavy_best = {"ngl": heavy_fit["ngl"], "threads": prof["cpu_physical"], "tok_s": None}
        heavy_results = []
    else:
        heavy_best, heavy_results = tune_model("heavy", heavy_path, heavy_fit, prof, cpu_only)
        heavy_fit = fit_model(heavy_entry, heavy_path, prof, ngl=heavy_best["ngl"])

    # Tiny Model
    gpu = prof.get("gpu")
    vram_free = (gpu["vram_free_gb"] - heavy_fit["gpu_gb"]) if gpu else None
    tiny_fit = fit_model(tiny_entry, tiny_path, prof, vram_free_gb=vram_free)
    
    if not tiny_fit["fits"]:
        raise SystemExit("Close apps to free RAM, or use a smaller model via --heavy.")

    if no_tune:
        tiny_best = {"ngl": tiny_fit["ngl"], "threads": prof["cpu_physical"], "tok_s": None}
        tiny_results = []
    else:
        tiny_best, tiny_results = tune_model("tiny", tiny_path, tiny_fit, prof, cpu_only)
        tiny_fit = fit_model(tiny_entry, tiny_path, prof, vram_free_gb=vram_free, ngl=tiny_best["ngl"])

    co_resident = (heavy_fit["ram_gb"] + tiny_fit["ram_gb"] <= prof["ram_available_gb"] - RAM_RESERVE_GB)

    heavy_cfg = {
        "key": heavy_key, "name": heavy_entry["name"], "path": str(heavy_path),
        "ngl": heavy_best["ngl"], "ctx": heavy_fit["ctx"], "threads": heavy_best["threads"],
        "placement": heavy_fit["placement"], "ram_gb": heavy_fit["ram_gb"], "tok_s": heavy_best["tok_s"]
    }
    tiny_cfg = {
        "key": tiny_key, "name": tiny_entry["name"], "path": str(tiny_path),
        "ngl": tiny_best["ngl"], "ctx": tiny_fit["ctx"], "threads": tiny_best["threads"],
        "placement": tiny_fit["placement"], "ram_gb": tiny_fit["ram_gb"], "tok_s": tiny_best["tok_s"]
    }

    profile_data = {
        "created": datetime.datetime.now().isoformat(),
        "profile": prof,
        "co_resident": co_resident,
        "models": {
            "heavy": heavy_cfg,
            "tiny": tiny_cfg
        },
        "tuning": {
            "heavy": heavy_results,
            "tiny": tiny_results
        }
    }

    PROFILES_DIR.mkdir(exist_ok=True)
    out_path = PROFILES_DIR / f"profile-{prof['backend']}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, indent=2)

    ui.tuning_table("heavy", heavy_entry["name"], heavy_results, heavy_best)
    ui.tuning_table("tiny", tiny_entry["name"], tiny_results, tiny_best)
    ui.setup_done(out_path, co_resident)

    return out_path
