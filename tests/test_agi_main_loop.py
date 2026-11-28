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


def test_main_loop_step_mode():
    from agi.tools import ToolRegistry, ToolSpec
    reg = ToolRegistry(); seen = []
    reg.register(ToolSpec("test.read", lambda a: {"ok": True}, "read", frozenset({"main"})))
    def decide(goal, trace, registry):
        seen.append(len(trace))
        if trace: return {"ok": True, "done": True}
        return {"ok": True, "done": False, "tool": "test.read", "args": {}}
    out = main_loop.run("x", reg, decide=decide)
    assert out["ok"] is True and len(out["steps"]) == 1
    assert seen == [0, 1]
