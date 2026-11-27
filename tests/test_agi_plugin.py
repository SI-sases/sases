from agi import plugin_bridge


def test_plugin_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SASES_PLUGIN_ALLOW", raising=False)
    assert plugin_bridge.enabled() is False
    assert plugin_bridge.list_plugins()["ok"] is False
