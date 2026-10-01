"""OWNER: Part 1 (Claude). Spec: fit.md. Decide whether a model fits and where it runs, before loading it."""
from .config import GB, RAM_RESERVE_GB, VRAM_OVERHEAD_GB


def fit_model(entry, model_path, prof, vram_free_gb=None, ngl=None) -> dict:
    size = model_path.stat().st_size / GB * 1.05          # weights + runtime buffers
    kv = entry["kv_gb_per_4k"] * entry["ctx"] / 4096      # KV cache estimate
    layers = entry["layers"]
    all_layers = layers + 1                               # +1 = output layer
    gpu = prof.get("gpu")
    free = (vram_free_gb if vram_free_gb is not None
            else (gpu["vram_free_gb"] if gpu else 0)) - VRAM_OVERHEAD_GB

    if ngl is None:
        if gpu and size + kv <= free:
            ngl = all_layers
        elif gpu and free - kv > 0.3:
            ngl = max(1, min(layers, int(layers * (free - kv) / size)))
        else:
            ngl = 0

    frac = ngl / all_layers
    gpu_gb = size * frac + (kv if ngl else 0)
    ram_gb = size * (1 - frac) + (0 if ngl else kv)
    placement = ("CPU only" if ngl == 0 else
                 "all layers on GPU" if ngl == all_layers else
                 f"{ngl}/{all_layers} layers on GPU, rest on CPU")
    return {
        "ngl": ngl, "all_layers": all_layers, "ctx": entry["ctx"],
        "threads": prof.get("cpu_physical") or prof.get("cpu_logical") or 1,
        "placement": placement,
        "size_gb": round(size, 2), "gpu_gb": round(gpu_gb, 2), "ram_gb": round(ram_gb, 2),
        "fits": ram_gb <= prof["ram_available_gb"] - RAM_RESERVE_GB,
    }
