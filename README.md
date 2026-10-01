# Squeeze

**Run the best open-weight models your hardware can handle—fully offline, fully private.**

Squeeze is a local, terminal-based AI pipeline designed to intelligently run multiple large language models on standard laptop hardware (no dedicated GPU required!). It dynamically swaps between models depending on the complexity of the task and the current memory available on your machine.

## How It Works

Squeeze orchestrates two models simultaneously:
1. **The Heavy Model (Qwen3-1.7B)**: The primary engine. Used for complex reasoning, planning, and coding.
2. **The Tiny Model (Qwen3-0.6B)**: The sidekick. Used for rapid documentation, summarization, and lightweight tasks, maximizing speed and minimizing memory overhead.

When Squeeze runs a task, it dynamically "flips" between these models based on the required operation. If your system runs out of RAM, Squeeze will gracefully unload the heavy model and fall back completely to the tiny model, ensuring your tasks always finish without crashing your computer.

### Zero-Data Privacy Guarantee
Squeeze runs locally via `llama.cpp`. A strict privacy guard monitors every step of the pipeline. Unless explicitly requested via the `--online` flag, Squeeze enforces a total network boundary—blocking all HTTP connections originating from the process. **Zero telemetry. Zero data exfiltration.**

*(Note: The privacy guard blocks HTTP traffic at the socket level. DNS resolution requests may still hit your system resolver before the traffic is blocked.)*

---

## Installation

1. **Clone and Install**
   ```bash
   git clone https://github.com/ahmedmustafakhan125-coder/MLH-Hackathon.git squeeze
   cd squeeze
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. **Download Models & Binaries**
   Squeeze requires the `Qwen3-0.6B-GGUF` and `Qwen3-1.7B-GGUF` models in `Q4_K_M` formats.
   Place them inside the `./models/` directory.
   Download the `llama.cpp` Windows CPU release and extract the binaries into the `./bin/` directory.

---

## Usage

Squeeze is entirely command-line driven.

### 1. Setup & Benchmarking
Before running Squeeze, you must run the initial setup. This profiles your hardware, validates that the models fit inside your available RAM, dynamically benchmarks different thread counts, and saves a configuration profile optimized for your exact machine.

```bash
python -m squeeze setup
```

### 2. Running a Task
To run Squeeze, simply pass your prompt to the `run` command.

```bash
python -m squeeze run "Write a Python function to validate an email address, including pytest tests."
```

#### Advanced Flags
- `--online`: Turns off the privacy guard to allow internet access.
- `--simulate-pressure-at N`: Forces a simulated memory out-of-bounds error before step `N` to test the fallback handling.
- `--min-free-gb X`: Tells Squeeze to panic and drop the heavy model if free RAM drops below `X` GB.
- `--cpu-only`: Forces the use of the CPU profile even if a GPU is detected.

---

## Architecture
- **Router**: Directs tasks to the appropriate model based on complexity.
- **Context Manager**: Dynamically resizes contexts. If the heavy model is unloaded due to memory constraints, the context manager actively truncates history to fit within the tiny model's strict 1024-token budget.
- **Tuner & Profiler**: Measures your physical/logical cores and tests candidate configurations in real-time to pick the absolute fastest token-generation parameters.
- **Pipeline**: Manages the loading, unloading, and graceful teardown of `llama-server` sub-processes.

---

## Future Roadmap
- **Multi-Model Swarm Integration**: Expand the architecture to dynamically route tasks across *N* models (e.g., dedicated vision models, coding specialists, and audio-transcription layers) rather than just two.
- **Rich Terminal UI**: A robust visual overhaul using the Python `rich` library to present syntax-highlighted code output, vibrant styling, and interactive multi-model planning grids.
- **Web UI & API Endpoints**: Serve the optimized, dynamic model pipeline over a seamless local web dashboard for broader usage beyond the terminal.
- **Plugin System**: Build a hook-based plugin architecture allowing users to easily slot in external tools (like search, RAG, and execution sandboxes) directly into Squeeze's private ecosystem.

---

## License
Squeeze is released under the **MIT License**. See the `LICENSE` file for full details.

### Third-Party Licenses
- **Models**: The Qwen3 weights used in the default configurations are licensed under the **Apache License 2.0**.
- **Inference Engine**: Squeeze relies heavily on `llama.cpp` for core LLM inference, which is provided under the **MIT License**.
