from core.services import tool_policy


def test_mcp_is_high_risk():
    assert tool_policy.risk("mcp.1.tool") == "high"


def test_shell_requires_approval(monkeypatch):
    monkeypatch.setenv("SASES_APPROVAL_MODE", "risk")
    assert tool_policy.requires_approval("run_python", {"code": "print(1)"})


def test_read_does_not_require_approval(monkeypatch):
    monkeypatch.setenv("SASES_APPROVAL_MODE", "risk")
    assert not tool_policy.requires_approval("file_read", {"file_path": "README.md"})


def test_mode_off(monkeypatch):
    monkeypatch.setenv("SASES_APPROVAL_MODE", "off")
    assert not tool_policy.requires_approval("mcp.1.tool", {})
