import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import agi_coordinator

def test_temperature_conversion_keyword():
    result = agi_coordinator.execute_task("将摄氏30度转换为华氏度")
    assert result["success"] is True
    assert result["module_id"] == "unit-converter"
    assert result["result"]["fahrenheit"] == 86.0

def test_temperature_conversion_keyword_reverse():
    result = agi_coordinator.execute_task("华氏86度等于多少摄氏度")
    assert result["success"] is True
    assert result["module_id"] == "unit-converter"
    assert result["result"]["celsius"] == 30.0

def test_no_matching_tool():
    # 这个任务没有对应工具，应返回失败
    result = agi_coordinator.execute_task("帮我分析股票市场趋势")
    assert result["success"] is False
