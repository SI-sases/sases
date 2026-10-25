import os
import sys
import pytest

# 确保可以导入 core 模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import seed_utils

def test_safe_run_tests_success():
    code = """
def add(a, b):
    return a + b
"""
    test_cases = [
        {"input": [1, 2], "expected_output": 3},
        {"input": [5, -3], "expected_output": 2},
    ]
    passed, msg, is_code = seed_utils.safe_run_tests(code, test_cases)
    assert passed is True
    assert is_code is True
    assert "通过" in msg

def test_safe_run_tests_failure():
    code = """
def multiply(a, b):
    return a * b
"""
    test_cases = [
        {"input": [2, 3], "expected_output": 7},  # 错误预期
    ]
    passed, msg, is_code = seed_utils.safe_run_tests(code, test_cases)
    assert passed is False
    assert "测试失败" in msg

def test_safe_run_tests_non_code():
    text = "这不是代码，只是一段中文说明。"
    passed, msg, is_code = seed_utils.safe_run_tests(text, [{"input": 1, "expected_output": 1}])
    assert passed is False
    assert is_code is False
    assert "非代码答案" in msg

def test_safe_run_tests_no_test_cases():
    code = """
def add(a, b):
    return a + b
"""
    passed, msg, is_code = seed_utils.safe_run_tests(code, [])
    assert passed is False
    assert is_code is False
    assert "无测试用例" in msg

def test_safe_run_tests_syntax_error():
    code = """
def add(a, b):
    return a + b
"""
    # 这个代码没有语法错误，我们构造一个语法错误
    bad_code = "def add(a, b): return a + b"  # 实际上是合法的
    # 造一个真正的语法错误：缺少冒号
    bad_code = "def add(a, b)\n    return a + b"
    test_cases = [{"input": [1, 2], "expected_output": 3}]
    passed, msg, is_code = seed_utils.safe_run_tests(bad_code, test_cases)
    # 注意：safe_run_tests 使用 exec 或 subprocess，语法错误会被捕获为执行出错
    assert passed is False
    # 可能返回“执行出错”或“测试失败”，这里只验证失败即可

def test_clean_code():
    code_with_markdown = "```python\ndef add(a, b):\n    return a + b\n```"
    cleaned = seed_utils.clean_code(code_with_markdown)
    assert cleaned == "def add(a, b):\n    return a + b"

def test_parse_two_branches():
    text = "思路A: 使用循环\n思路B: 使用递归"
    branch_a, branch_b = seed_utils.parse_two_branches(text)
    assert branch_a == "使用循环"
    assert branch_b == "使用递归"
