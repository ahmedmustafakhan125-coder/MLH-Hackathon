"""Fails until every module exposes the names in CONTRACTS.md. Run: pytest -q tests/test_contract.py"""
import inspect

from squeeze import bootstrap, context, fit, pipeline, privacy, profiler, router, server, tune, ui

UI_FUNCS = {
    "status": 1, "hardware_table": 1, "tuning_table": 4, "setup_done": 2, "run_header": 3,
    "privacy_banner": 1, "loaded": 3, "plan": 3, "flip": 3, "pressure": 2, "step_line": 2,
    "summary": 4, "privacy_line": 1, "output_path": 1,
}


def test_ui_signatures():
    for name, n in UI_FUNCS.items():
        fn = getattr(ui, name)
        assert len(inspect.signature(fn).parameters) == n, name


def test_names_exist():
    assert callable(router.route) and router.ALLOWED_KINDS and router.HEAVY_KINDS
    assert context.TaskState and callable(context.build_packet) and callable(context.approx_tokens)
    assert isinstance(privacy.LEDGER, dict) and callable(privacy.enable_offline) and callable(privacy.verify)
    assert callable(fit.fit_model)
    assert callable(pipeline.run_task) and callable(pipeline.parse_plan)
    assert callable(profiler.profile)
    assert server.LlamaServer and callable(server.find_server_binary)
    assert callable(tune.candidates) and callable(tune.tune_model)
    assert callable(bootstrap.run_setup)
