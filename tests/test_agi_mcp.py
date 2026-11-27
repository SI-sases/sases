from agi import mcp_bridge


def test_mcp_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SASES_MCP_ALLOW", raising=False)
    assert mcp_bridge.enabled() is False
    assert mcp_bridge.list_servers()["ok"] is False
