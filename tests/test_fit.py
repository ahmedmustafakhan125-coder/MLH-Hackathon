import json
from types import SimpleNamespace

import pytest

from squeeze.config import GB, REGISTRY_PATH
from squeeze.fit import fit_model

REGISTRY = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
PROFILE = {"cpu_physical": 4, "cpu_logical": 8, "ram_total_gb": 15.8, "ram_available_gb": 9.2, "gpu": None}


class FakeModelFile:
    """fit_model only calls .stat().st_size, so no multi-GB file is needed."""
    def __init__(self, gb):
        self._size = int(gb * GB)

    def stat(self):
        return SimpleNamespace(st_size=self._size)


def test_cpu_laptop_1_7b():
    r = fit_model(REGISTRY["qwen3-1.7b"], FakeModelFile(1.105), PROFILE)
    assert r["ngl"] == 0 and r["placement"] == "CPU only" and r["fits"] is True
    assert r["all_layers"] == 29 and r["ctx"] == 4096 and r["threads"] == 4
    assert r["size_gb"] == 1.16 and r["gpu_gb"] == 0.0 and r["ram_gb"] == 1.6


def test_expected_ram_for_each_model():
    expected = {"qwen3-0.6b": (0.40, 0.9), "qwen3-1.7b": (1.105, 1.6), "qwen3-4b": (2.3, 3.0)}
    for key, (file_gb, approx_ram) in expected.items():
        r = fit_model(REGISTRY[key], FakeModelFile(file_gb), PROFILE)
        assert r["fits"] and abs(r["ram_gb"] - approx_ram) < 0.3, key


def test_does_not_fit_when_ram_is_short():
    low = dict(PROFILE, ram_available_gb=2.5)          # 1.6 GB needed, only 0.5 GB usable after the reserve
    assert fit_model(REGISTRY["qwen3-1.7b"], FakeModelFile(1.105), low)["fits"] is False


def test_threads_fall_back_when_physical_cores_unknown():
    prof = dict(PROFILE, cpu_physical=None)
    assert fit_model(REGISTRY["qwen3-1.7b"], FakeModelFile(1.0), prof)["threads"] == 8


GPU = {"name": "RTX", "vram_total_gb": 8.0, "vram_free_gb": 6.0}


def test_gpu_all_layers():
    r = fit_model(REGISTRY["qwen3-1.7b"], FakeModelFile(1.105), dict(PROFILE, gpu=GPU))
    assert r["ngl"] == 29 and r["placement"] == "all layers on GPU"
    assert r["gpu_gb"] == 1.6 and r["ram_gb"] == 0.0


def test_gpu_partial_offload():
    r = fit_model(REGISTRY["qwen3-1.7b"], FakeModelFile(10.0), dict(PROFILE, gpu=GPU))
    assert 0 < r["ngl"] < 29
    assert r["placement"] == f"{r['ngl']}/29 layers on GPU, rest on CPU"


def test_vram_override_and_ngl_override():
    prof = dict(PROFILE, gpu=GPU)
    assert fit_model(REGISTRY["qwen3-1.7b"], FakeModelFile(1.105), prof, vram_free_gb=0.5)["ngl"] == 0
    r = fit_model(REGISTRY["qwen3-1.7b"], FakeModelFile(1.105), prof, ngl=0)       # tuner forcing CPU-only
    assert r["placement"] == "CPU only" and r["ram_gb"] == 1.6
    assert fit_model(REGISTRY["qwen3-1.7b"], FakeModelFile(1.105), prof, ngl=10)["placement"].startswith("10/29")
