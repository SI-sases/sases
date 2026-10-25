import os
import sys
import importlib.util
import pytest

# 确保可以导入项目模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def load_harness_run(module_dir: str, entrypoint: str = "main.py"):
    """加载指定 Harness 模块的 run 函数"""
    module_path = os.path.join("harness_modules", module_dir, entrypoint)
    spec = importlib.util.spec_from_file_location(f"harness_{module_dir}", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run

def test_calculator_addition():
    run = load_harness_run("calculator")
    result = run({"expression": "2+3*4"})
    assert result == {"result": 14}

def test_calculator_parentheses():
    run = load_harness_run("calculator")
    result = run({"expression": "(2+3)*4"})
    assert result == {"result": 20}

def test_calculator_invalid_expression():
    run = load_harness_run("calculator")
    with pytest.raises(ValueError):
        run({"expression": "2+"})

def test_calculator_illegal_operation():
    run = load_harness_run("calculator")
    with pytest.raises(ValueError):
        run({"expression": "__import__('os').system('dir')"})

def test_text_stats_basic():
    run = load_harness_run("text_stats")
    text = "Hello world\nThis is a test.\nHello again"
    result = run({"text": text})
    assert result["char_count"] == len(text)
    assert result["word_count"] == 8  # Hello world This is a test Hello again
    assert result["line_count"] == 3
    assert result["top_words"]["hello"] == 2

def test_json_formatter_pretty():
    run = load_harness_run("json_formatter")
    result = run({"json_string": '{"name":"test","value":123}', "indent": 2})
    assert '"name": "test"' in result["formatted"]

def test_json_formatter_compact():
    run = load_harness_run("json_formatter")
    result = run({"json_string": '{"name":"test","value":123}', "indent": 0})
    assert '{"name":"test","value":123}' in result["formatted"]

def test_json_formatter_invalid_json():
    run = load_harness_run("json_formatter")
    with pytest.raises(ValueError):
        run({"json_string": '{"name": "test",}'})

def test_base64_encode_decode():
    run = load_harness_run("base64_codec")
    encoded = run({"action": "encode", "text": "hello"})
    assert encoded == {"result": "aGVsbG8="}
    decoded = run({"action": "decode", "text": "aGVsbG8="})
    assert decoded == {"result": "hello"}

def test_base64_invalid_decode():
    run = load_harness_run("base64_codec")
    with pytest.raises(ValueError):
        run({"action": "decode", "text": "not_base64!!"})

def test_string_utils_reverse():
    run = load_harness_run("string_utils")
    result = run({"operation": "reverse", "text": "abc"})
    assert result == {"result": "cba"}

def test_string_utils_upper():
    run = load_harness_run("string_utils")
    result = run({"operation": "upper", "text": "abc"})
    assert result == {"result": "ABC"}

def test_string_utils_lower():
    run = load_harness_run("string_utils")
    result = run({"operation": "lower", "text": "ABC"})
    assert result == {"result": "abc"}

def test_string_utils_capitalize():
    run = load_harness_run("string_utils")
    result = run({"operation": "capitalize", "text": "hello world"})
    assert result == {"result": "Hello world"}

def test_string_utils_invalid_operation():
    run = load_harness_run("string_utils")
    with pytest.raises(ValueError):
        run({"operation": "unknown", "text": "abc"})
