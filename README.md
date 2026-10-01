# Squeeze
Run the best open-weight models your hardware can handle: no GPU needed, fully private.

## Why
Open models are good, but on normal laptops they're slow, crash, or need manual tuning. Cloud AI sends your code off your machine. Squeeze solves this by profiling your CPU and RAM, benchmarking thread configurations, routing tasks dynamically between a heavy model and a tiny model, and executing completely offline.

## What it does
- **Profiles your hardware**: Automatically detects OS, physical/logical CPU cores, total/available RAM, and GPU (NVIDIA or CPU-only).
- **Fits and auto-tunes**: Tests and benchmarks real token generation speed across thread counts to pick the optimal configuration.
- **Dynamic two-model routing**: Routes complex steps (planning, coding, testing) to the heavy model and lightweight steps (docs, summaries) to the tiny model.
- **Context rebuild on model flip**: Intelligently compacts and rebuilds the context window when switching models or handling memory pressure.
- **Memory-pressure recovery**: Detects RAM constraints and unloads heavy models to preserve stability without losing execution state.
- **Private by default**: Blocks all off-device outbound connections at the socket level and records every blocked attempt into an audit ledger.

## Quickstart

### 1. Prerequisites & Installation
```powershell
# 1. Clone repository and set up virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt
```

### 2. Run Setup & Profile
```powershell
# Profile hardware and auto-tune models
python -m squeeze setup
```

### 3. Execute a Task Privately
```powershell
# Run a task with simulated memory pressure trigger
python -m squeeze run "Write a Python function validate_email(s) that returns True or False, with pytest tests and short usage docs." --simulate-pressure-at 2
```

### 4. Preview UI Mockups (No Models Required)
```powershell
# Run standalone Rich terminal UI preview
python scripts/ui_preview.py
```

## Tested on
- **Hardware**: Intel Core i5 (11th gen), 16 GB RAM, no dedicated GPU, Windows 11
- **Cloud Reference**: DigitalOcean 8 vCPU / 16 GB RAM droplet, Ubuntu 24.04

### Measured Performance
- **Heavy Model (Qwen3-1.7B)**: `<fill after test: ~19.4 tok/s on 4 threads>`
- **Tiny Model (Qwen3-0.6B)**: `<fill after test: ~42.0 tok/s on 4 threads>`
- **Total Run Time**: `<fill after test: ~61s for 4-step pipeline>`

## Models and Licenses
- **Qwen3-1.7B & Qwen3-0.6B** (and optionally Qwen3-4B): [Apache-2.0 License](https://huggingface.co/Qwen)
- **Inference Engine**: [llama.cpp](https://github.com/ggerganov/llama.cpp) (MIT License), executed as an external local binary

## What's Original
The complete Squeeze execution harness:
- Automated hardware profiler and memory-fit engine.
- Real-time token rate benchmarking tuner for CPU threads.
- Two-model task router with fallback and escalation paths.
- Resilient context window reconstruction across model handoffs.
- Memory-pressure detection and dynamic model unloading.
- In-process socket-level privacy guard and audit ledger.
- ASCII-safe Rich terminal user interface.

## Privacy: What's Guaranteed and What Isn't

| Layer / Vector | Guaranteed | Not Guaranteed |
|---|---|---|
| **Squeeze Process Connections** | **Yes**: Outbound TCP connections are intercepted and blocked at the socket level, logged to the privacy ledger. | Non-Python processes running on the host OS. |
| **Data Exfiltration** | **Yes**: Prompts, task state, generated code, and intermediate outputs never leave localhost (`127.0.0.1`). | Compromised host OS or physical device access. |
| **DNS Lookups** | Intercepted when `getaddrinfo` is hooked; local addresses allowed. | OS resolver caching before application start. |
| **Local Inference** | **Yes**: llama.cpp runs strictly on local loopback ports (`8081`, `8082`). | External cloud API calls (disabled by design). |

## Next Steps
- OpenAI-compatible `serve` endpoint for local tooling.
- VS Code extension for seamless in-editor code generation.
- Integrated graphics acceleration (Vulkan / SYCL).
- Mixture-of-Experts (MoE) partial offloading.
- Speculative decoding combining tiny and heavy models.

## Demo Video
- [Demo Video Link](<fill after test>)

## License
[MIT License](LICENSE)
