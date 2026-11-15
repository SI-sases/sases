"""SASES 自愈引擎 · 4 阶段 + 4 防呆"""
import os
import re
import ast
import subprocess
import importlib
from datetime import datetime

from ..db import db_cursor
from .swarm.llm_parser import _call_llm

_heal_count = {}
HEAL_MAX_PER_TASK = 1

FORBIDDEN_FILES = ['bootstrap.py', 'users.db', '.env', 'secret_key.bin', 'api_key_encryption.key']
READONLY_KEYWORDS = ['探测', '列出', '查看', '统计', '搜索', '读']


def _short_log(log, n=2000):
    return log[-n:] if len(log) > n else log


def _extract_file_path(error_log):
    patterns = [
        r'File "([^"]+\.py)"',
        r"File '([^']+\.py)'",
        r'([a-zA-Z]:\\[^\s:]+\.py)',
        r'(core/[^\s:]+\.py)',
    ]
    for p in patterns:
        m = re.search(p, error_log)
        if m:
            return m.group(1)
    return ''


def _is_forbidden(file_path):
    if not file_path:
        return True
    name = os.path.basename(file_path)
    for f in FORBIDDEN_FILES:
        if f in file_path or name == f:
            return True
    return False


def _is_readonly_task(user_input):
    return any(kw in user_input for kw in READONLY_KEYWORDS)


def _get_standard_answer(file_path):
    try:
        r = subprocess.run(['git', 'show', f'HEAD:{file_path}'],
                          capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout
    except Exception:
        pass
    try:
        if os.path.exists(file_path):
            return open(file_path, encoding='utf-8').read()
    except Exception:
        pass
    return ''


async def _generate_fix_script(file_path, error_log, original_code):
    prompt = f"""你是 SASES 自愈引擎。生成一段 Python 脚本修复以下文件。

文件: {file_path}
真实源码:
{chr(10).join(original_code.split(chr(10))[:150])}

text
报错:
{_short_log(error_log)}

text

要求: 脚本必须用 open(file_path,'w') 写入完整修复后代码，必须 py_compile 校验，输出纯代码无解释。"""
    try:
        raw = (await _call_llm(prompt, max_tokens=8000)).strip()
        if raw.startswith('```'):
            lines = raw.split('\n')
            lines = lines[1:] if lines[0].startswith('```') else lines
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            raw = '\n'.join(lines)
        return raw
    except Exception:
        return ''


def _execute_fix_script(script_code):
    try:
        ast.parse(script_code)
    except SyntaxError as e:
        return False, f'脚本语法错: {e}'
    try:
        exec(script_code, {'__name__': '__heal__'})
        return True, 'exec OK'
    except Exception as e:
        return False, f'exec 失败: {e}'


def _validate_after_fix(file_path):
    if not os.path.exists(file_path):
        return False, '文件不存在'
    try:
        subprocess.run(['python', '-m', 'py_compile', file_path],
                       capture_output=True, timeout=10, check=True)
        return True, 'py_compile OK'
    except Exception as e:
        return False, f'校验失败: {e}'


def _reload_module(file_path):
    try:
        rel = os.path.relpath(file_path, 'core')
        mod = 'core.' + rel.replace(os.sep, '.').replace('.py', '')
        if mod in importlib.sys.modules:
            importlib.reload(importlib.sys.modules[mod])
        return True
    except Exception:
        return False


async def try_heal(task_id, error_log, user_input=''):
    cnt = _heal_count.get(task_id, 0)
    if cnt >= HEAL_MAX_PER_TASK:
        print(f'[healer] {task_id} 已自愈 {cnt} 次，拒绝')
        return False
    if _is_readonly_task(user_input):
        print(f'[healer] 只读任务，跳过')
        return False
    file_path = _extract_file_path(error_log)
    if not file_path:
        print(f'[healer] 无法提取文件路径')
        return False
    if _is_forbidden(file_path):
        print(f'[healer] {file_path} 在白名单')
        return False
    if not os.path.exists(file_path):
        print(f'[healer] {file_path} 不存在')
        return False

    print(f'[healer] 开始自愈 {task_id} -> {file_path}')
    _heal_count[task_id] = cnt + 1

    original = _get_standard_answer(file_path)
    if not original:
        print(f'[healer] 无法获取源码')
        return False

    print(f'[healer] 阶段2: 生成修复脚本')
    fix_script = await _generate_fix_script(file_path, error_log, original)
    if not fix_script or ('open(' not in fix_script and 'write' not in fix_script):
        print(f'[healer] 脚本无效')
        return False

    print(f'[healer] 阶段3: 执行手术')
    ok, msg = _execute_fix_script(fix_script)
    if not ok:
        print(f'[healer] 手术失败: {msg}')
        return False

    ok, msg = _validate_after_fix(file_path)
    if not ok:
        print(f'[healer] 校验失败: {msg}')
        return False

    print(f'[healer] 阶段4: 热重载')
    _reload_module(file_path)

    try:
        with db_cursor(commit=True) as cur:
            cur.execute("""INSERT INTO heal_log
                (task_id, file_path, error_log, fix_script, status, created_at)
                VALUES (?, ?, ?, ?, 'success', ?)""",
                (task_id, file_path, _short_log(error_log, 500),
                 fix_script[:2000], datetime.now().isoformat()))
    except Exception:
        pass

    print(f'[healer] 自愈成功')
    return True


def get_heal_count(task_id):
    return _heal_count.get(task_id, 0)


def reset_heal_count(task_id):
    _heal_count.pop(task_id, None)
