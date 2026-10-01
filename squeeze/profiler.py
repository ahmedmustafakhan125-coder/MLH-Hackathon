import os, platform
import psutil
from .config import GB

def profile(cpu_only: bool = False) -> dict:
    vm = psutil.virtual_memory()
    prof = {
        "os": platform.system(),
        "machine": platform.machine(),
        "cpu_physical": psutil.cpu_count(logical=False) or os.cpu_count() or 1,
        "cpu_logical": psutil.cpu_count(logical=True) or os.cpu_count() or 1,
        "ram_total_gb": round(vm.total / GB, 1),
        "ram_available_gb": round(vm.available / GB, 1),
        "gpu": None if cpu_only else _nvidia_gpu(),
    }
    prof["backend"] = "cuda" if prof["gpu"] else "cpu"
    return prof

def _nvidia_gpu():
    try:
        import pynvml
        pynvml.nvmlInit()
        try:
            if pynvml.nvmlDeviceGetCount() < 1:
                return None
            h = pynvml.nvmlDeviceGetHandleByIndex(0)
            name = pynvml.nvmlDeviceGetName(h)
            name = name.decode() if isinstance(name, bytes) else name
            mem = pynvml.nvmlDeviceGetMemoryInfo(h)
            return {"name": name, "vram_total_gb": round(mem.total / GB, 1),
                    "vram_free_gb": round(mem.free / GB, 1)}
        finally:
            pynvml.nvmlShutdown()
    except Exception:
        return None          # no NVIDIA driver = CPU path (expected on your laptop)
