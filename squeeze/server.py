"""OWNER: Part 2 (Antigravity). Spec: server.md. STUB - replace me."""


def find_server_binary() -> str:
    raise NotImplementedError("server.find_server_binary - Part 2 (Antigravity)")


class LlamaServer:
    def __init__(self, role, model_path, port, ngl, ctx, threads, cpu_only=False):
        self.role, self.model_path, self.port = role, model_path, port
        self.ngl, self.ctx, self.threads, self.cpu_only = ngl, ctx, threads, cpu_only
        self.load_seconds = 0.0

    def start(self, timeout=180):
        raise NotImplementedError("LlamaServer.start - Part 2 (Antigravity)")

    def stop(self):
        pass

    def chat(self, messages, max_tokens):
        raise NotImplementedError("LlamaServer.chat - Part 2 (Antigravity)")
