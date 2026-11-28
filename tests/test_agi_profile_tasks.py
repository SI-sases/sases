import sqlite3

from agi.executor import execute
from agi.package import TaskPackage
from agi.profile_tasks import bilibili_signature_steps, youtube_profile_steps
from agi.tools import ToolRegistry, ToolSpec


def test_profile_task_templates_are_sases_browser_steps():
    bili = bilibili_signature_steps("hello")
    assert bili[0]["tool"] == "browser.open"
    assert any(s["tool"] == "browser.fill_targets" for s in bili)
    yt = youtube_profile_steps("desc", "GitHub", "https://github.com/SI-sases/sases")
    assert any(s["tool"] == "browser.click_target" for s in yt)


def test_duplicate_browser_action_is_suppressed():
    reg = ToolRegistry()
    reg.register(ToolSpec("browser.test", lambda a: {"ok": True}, "read", frozenset({"sub"})))
    step = {"tool": "browser.test", "args": {"x": 1}}
    pkg = TaskPackage(goal="loop", node_id="local", acceptance=["done"],
                      steps=[step, step, step], tools_allowed=["browser.test"])
    out = execute(pkg, reg, sqlite3.connect(":memory:"), profile="sub")
    assert out["ok"] is False
    assert out["error"] == "duplicate_action_suppressed"
