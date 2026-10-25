import json
import os
import re
import subprocess
import tempfile
import inspect


def is_python_code(text):
    """判断文本是否包含Python函数定义"""
    return bool(re.search(r'\bdef\s+\w+\s*\(', text)) or bool(re.search(r'\bclass\s+\w+', text))


def safe_run_tests(code, test_cases, timeout=5):
    """
    在隔离沙箱中运行代码并执行测试用例。
    返回 (passed, message, is_code)
    """
    if not test_cases:
        return False, "无测试用例", False

    if not is_python_code(code):
        return False, "非代码答案", False

    # 清理代码，移除 __main__ 调用和函数调用
    code = re.sub(r"if __name__\s*==\s*['\"]__main__['\"]:\s*\n.*", "", code, flags=re.DOTALL)
    code = re.sub(r"\n\s*\w+\(\)", "", code)

    # 提取第一个函数名
    func_match = re.search(r"def (\w+)", code)
    if not func_match:
        return False, "无函数定义", False
    func_name = func_match.group(1)

    # 将函数重命名为 __test_func__，避免与测试代码冲突
    code_renamed = re.sub(r'def\s+' + func_name + r'\b', 'def __test_func__', code, count=1)

    for case in test_cases:
        inp = case.get("input", [])
        expected = case.get("expected_output")
        expected_repr = repr(expected)

        full_test = f"""
{code_renamed}
import json, sys, inspect
try:
    func = __test_func__
    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    if isinstance({json.dumps(inp)}, list):
        if len(params) == 1:
            result = func({json.dumps(inp)})
        elif len(params) == len({json.dumps(inp)}):
            result = func(*{json.dumps(inp)})
        else:
            result = func({json.dumps(inp)})
    else:
        result = func({json.dumps(inp)})
    passed = (result == {expected_repr})
    print(json.dumps({{"passed": passed, "output": str(result)}}))
except Exception as e:
    print(json.dumps({{"passed": False, "error": str(e)}}))
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(full_test)
            tmp_path = f.name

        try:
            proc = subprocess.run(["python", tmp_path], capture_output=True, text=True, timeout=timeout)
            if proc.returncode != 0:
                return False, f"执行出错: {proc.stderr.strip()}", True
            result = json.loads(proc.stdout.strip())
            if not result.get("passed", False):
                return False, f"测试失败: {result}", True
        except subprocess.TimeoutExpired:
            return False, "执行超时", True
        finally:
            os.unlink(tmp_path)

    return True, "全部测试通过", True
