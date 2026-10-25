import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.harness_runtime import HarnessRuntime

@pytest.fixture
def runtime():
    return HarnessRuntime()

def test_list_tools(runtime):
    tools = runtime.list_tools()
    # 至少应包含示例模块
    assert any(t.module_id == "unit-converter" for t in tools)

def test_invoke_tool_celsius_to_fahrenheit(runtime):
    resp = runtime.invoke_tool("unit-converter", {"celsius": 30})
    assert resp.success is True
    assert resp.result["fahrenheit"] == 86.0

def test_invoke_tool_fahrenheit_to_celsius(runtime):
    resp = runtime.invoke_tool("unit-converter", {"fahrenheit": 86})
    assert resp.success is True
    assert resp.result["celsius"] == 30.0

def test_invoke_nonexistent_module(runtime):
    resp = runtime.invoke_tool("nonexistent", {})
    assert resp.success is False
    assert "not found" in resp.error
