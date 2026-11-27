import os

from agi.planner import plan, to_package
from agi.tools import build_default_registry


def test_fallback_planner_is_bounded(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    registry = build_default_registry()
    result = plan("检查深圳状态", registry, max_steps=3)
    assert result["ok"] is True
    assert result["mode"] == "fallback"
    assert len(result["steps"]) <= 3
    assert all(s["tool"] in {t.id for t in registry.for_profile("main")} for s in result["steps"])


def test_to_package_limits_tools(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    registry = build_default_registry()
    result = plan("检查状态", registry)
    package = to_package("检查状态", "local", result["steps"])
    assert package.steps
    assert package.tools_allowed
