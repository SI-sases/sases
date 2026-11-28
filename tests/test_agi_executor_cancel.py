import sqlite3

from agi.executor import execute
from agi.package import TaskPackage
from agi.tools import ToolRegistry, ToolSpec


def test_executor_stops_when_cancelled():
    reg = ToolRegistry()
    reg.register(ToolSpec("test.noop", lambda a: {"ok": True}, "read", frozenset({"sub"})))
    pkg = TaskPackage(goal="cancel", node_id="local", acceptance=["done"],
                      steps=[{"tool": "test.noop", "args": {}}, {"tool": "test.noop", "args": {}}],
                      tools_allowed=["test.noop"])
    calls = {"n": 0}

    def should_continue():
        calls["n"] += 1
        return calls["n"] == 1

    out = execute(pkg, reg, sqlite3.connect(":memory:"), profile="sub",
                  should_continue=should_continue)
    assert out["ok"] is False
    assert out.get("cancelled") is True
