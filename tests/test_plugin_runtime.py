from core.services import plugin_registry, plugin_runtime


def test_plugin_tool_runs_when_enabled(monkeypatch):
    monkeypatch.setenv("SASES_PLUGIN_ALLOW", "1")
    plugin_registry.set_enabled("example-tool", True)
    try:
        result = plugin_runtime.run_tool("example-tool", {"x": 1})
        assert result["result"]["echo"]["x"] == 1
    finally:
        plugin_registry.set_enabled("example-tool", False)


def test_plugin_tool_disabled(monkeypatch):
    monkeypatch.setenv("SASES_PLUGIN_ALLOW", "1")
    plugin_registry.set_enabled("example-tool", False)
    try:
        plugin_runtime.run_tool("example-tool", {})
    except RuntimeError as exc:
        assert "disabled" in str(exc)
        return
    raise AssertionError("disabled plugin should fail")
