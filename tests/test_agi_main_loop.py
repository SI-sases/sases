from agi import main_loop
from agi.tools import ToolRegistry, ToolSpec


def test_main_loop_executes_read_only_steps(monkeypatch):
    reg = ToolRegistry()
    reg.register(ToolSpec("test.read", lambda a: {"ok": True, "value": 1}, "read",
                          frozenset({"main"})))
    monkeypatch.setattr(main_loop, "plan", lambda *a, **k: {
        "mode": "test", "steps": [{"tool": "test.read", "args": {}}]})
    out = main_loop.run("read", reg)
    assert out["ok"] is True
    assert out["steps"][0]["tool"] == "test.read"
    assert "只读" in main_loop.markdown(out)
