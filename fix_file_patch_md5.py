import os
import shutil
import ast
from datetime import datetime

FP_PATH = "harness_modules/file_patch/main.py"
backup_dir = ".backups"
os.makedirs(backup_dir, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
backup_path = os.path.join(backup_dir, f"harness_modules__file_patch__main.py.{ts}.bak")
shutil.copy2(FP_PATH, backup_path)
print(f"备份: {backup_path}")

with open(FP_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# 改动 1：加 import hashlib
if 'import hashlib' not in content:
    content = content.replace(
        'from datetime import datetime',
        'from datetime import datetime\nimport hashlib',
        1
    )
    print("改动 1: 加了 import hashlib")

# 改动 2：加 _file_md5 函数
if '_file_md5' not in content:
    content = content.replace(
        'def _validate_path(file_path: str) -> str:',
        '''def _file_md5(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None


def _validate_path(file_path: str) -> str:''',
        1
    )
    print("改动 2: 加了 _file_md5 函数")

# 改动 3a：run 函数开头加 MD5 记录
old_run_head = '''def run(params):
    result = _run_inner(params)'''
new_run_head = '''def run(params):
    _fp = params.get('file_path') or ''
    _before_md5 = None
    _abs_path_check = None
    try:
        _sp = _validate_path(_fp)
        _abs_path_check = os.path.abspath(_sp)
        if os.path.exists(_abs_path_check):
            _before_md5 = _file_md5(_abs_path_check)
    except Exception:
        pass

    result = _run_inner(params)'''

if '_before_md5' not in content:
    content = content.replace(old_run_head, new_run_head, 1)
    print("改动 3a: run 函数开头加 MD5 记录")

# 改动 3b：return result 前加 MD5 对比
old_return = '''                result['success'] = False
                result['syntax_error'] = err
                result['error'] = 'SYNTAX_ERROR: ' + err
    return result'''

new_return = '''                result['success'] = False
                result['syntax_error'] = err
                result['error'] = 'SYNTAX_ERROR: ' + err

    # v2.5.0: MD5 对比防假成功
    if isinstance(result, dict) and result.get('success') and _abs_path_check:
        _after_md5 = _file_md5(_abs_path_check)
        result['before_md5'] = _before_md5
        result['after_md5'] = _after_md5
        if _before_md5 is None and _after_md5 is None:
            result['success'] = False
            result['error'] = 'NO_FILE: 写入后文件仍不存在'
        elif _before_md5 is not None and _before_md5 == _after_md5:
            result['success'] = False
            result['error'] = 'NO_CHANGE: 文件内容未发生任何变化（old_snippet 与 new_snippet 可能相同）'

    return result'''

if '_after_md5' not in content:
    content = content.replace(old_return, new_return, 1)
    print("改动 3b: run 函数加 MD5 对比逻辑")

# 语法检查
try:
    ast.parse(content)
    print("语法检查通过")
except SyntaxError as e:
    print(f"语法检查失败: {e}")
    print("回滚...")
    shutil.copy2(backup_path, FP_PATH)
    raise SystemExit(1)

# 写入
with open(FP_PATH, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"已写入 {FP_PATH}")
print(f"新文件大小: {os.path.getsize(FP_PATH)} 字节")