"""Shared constants. FROZEN: changes need agreement from all three parts (see CONTRACTS.md)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
BIN_DIR = ROOT / "bin"
PROFILES_DIR = ROOT / "profiles"
OUT_DIR = ROOT / "out"
LOG_DIR = ROOT / "logs"
REGISTRY_PATH = ROOT / "models.json"

GB = 1024 ** 3
PORTS = {"heavy": 8081, "tiny": 8082}
DEFAULT_HEAVY = "qwen3-1.7b"
DEFAULT_TINY = "qwen3-0.6b"
RAM_RESERVE_GB = 2.0        # always leave this for Windows + browser
VRAM_OVERHEAD_GB = 0.6      # only used on machines with an NVIDIA GPU

MAX_TOKENS = {"plan": 250, "code": 500, "test": 400, "docs": 250, "summarize": 120}
CTX_MARGIN = 256            # safety gap between packet + output and the context size
PRESSURE_CTX_BUDGET = 1024  # packet cap once memory pressure has hit
