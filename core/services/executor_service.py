# core/services/executor_service.py
"""
后端进程内的蜂群执行器
- 从 swarm_pending_tasks 表读取待处理任务
- 执行命令或 harness 工具
- 通过 swarm_service.handle_step_done 汇报结果
"""
import asyncio
import json
import re
import subprocess
import datetime
from typing import Optional, Dict, Any, List

from ..db import db_cursor
from . import swarm_service
from ..harness_runtime import harness_runtime


# ========== 安全配置 ==========

ALLOWED_COMMANDS = {
    "dir", "ls", "tree",
    "type", "cat", "head", "tail",
    "findstr", "find", "grep", "where",
    "echo", "pwd", "cd", "whoami", "hostname",
    "wc",
    "python", "python3", "py",
    "pip", "pip3",
    "node", "npm", "npx",
    "git",
    "curl", "wget",
    "mkdir", "md",
    "copy", "xcopy", "move", "mv",
    "del", "rm",
    "ren", "rename",
    "set", "env",
    "tasklist", "taskkill",
    "netstat", "ping", "ipconfig",
    "sort", "uniq",
}

# 只保留真正危险的字符（命令链、替换、换行）
# 移除 % $ ^ < > 因为这些在合法路径/URL/输出中很常见
DANGEROUS_CHARS = ['&', '`', '\n', '\r']

MAX_OUTPUT_LENGTH = 20000
DEFAULT_TIMEOUT = 120
POLL_INTERVAL = 3
MAX_CONCURRENT_TASKS = 3

# ========== 内存状态 ==========

_running_task_ids: set = set()
_global_semaphore: Optional[asyncio.Semaphore] = None


def _get_semaphore() -> asyncio.Semaphore:
    global _global_semaphore
    if _global_semaphore is None:
        _global_semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    return _global_semaphore


# ========== 命令安全检查 ==========

def _looks_like_harness_prefix(cmd) -> bool:
    """检测 command 字段里误写的 harness 调用前缀。
    支持半角冒号 'harness:' 和全角冒号 'harness：'。"""
    if not isinstance(cmd, str):
        return False
    s = cmd.strip().lower()
    return s.startswith("harness:") or s.startswith("harness：")


def is_command_safe(cmd) -> tuple:
    """检查命令是否安全。支持 str 和 dict 两种输入。"""
    # dict 形式的 harness 调用：直接放行
    if isinstance(cmd, dict):
        if cmd.get('module_id') or cmd.get('type') == 'harness':
            return True, ''
        cmd = str(cmd)
    if not isinstance(cmd, str):
        cmd = str(cmd)
    if not cmd or not cmd.strip():
        return False, "命令为空"

    # JSON 形式的 harness 调用绕过 shell 字符检查
    _stripped = cmd.strip()
    if _stripped.startswith('{') and 'module_id' in _stripped:
        return True, ''

    # 危险字符检查（精简版）
    for ch in DANGEROUS_CHARS:
        if ch in cmd:
            return False, f"包含禁止字符: {repr(ch)}"

    parts = [p.strip() for p in cmd.split('|')]
    if any(not p for p in parts):
        return False, "存在空的管道段"

    for part in parts:
        tokens = part.split()
        if not tokens:
            continue
        base = tokens[0].lower()
        if base.endswith('.exe') or base.endswith('.bat') or base.endswith('.cmd'):
            base = base.rsplit('.', 1)[0]
        if base not in ALLOWED_COMMANDS:
            return False, f"命令不在白名单: {base}"

    return True, ""


def smart_decode(raw_bytes: bytes) -> str:
    if not raw_bytes:
        return ""
    for enc in ["utf-8", "gbk", "latin-1"]:
        try:
            return raw_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


# ========== 命令执行 ==========

def _win_path_fix(cmd):
    if not cmd:
        return cmd
    parts = cmd.split()
    if not parts:
        return cmd
    first = parts[0].lower()
    win_cmds = (chr(102)+chr(105)+chr(110)+chr(100)+chr(115)+chr(116)+chr(114), chr(116)+chr(121)+chr(112)+chr(101), chr(100)+chr(105)+chr(114), chr(116)+chr(114)+chr(101)+chr(101), chr(119)+chr(104)+chr(101)+chr(114)+chr(101), chr(109)+chr(111)+chr(114)+chr(101), chr(99)+chr(97)+chr(116))
    if first not in win_cmds:
        return cmd
    new_parts = [parts[0]]
    for p in parts[1:]:
        # v0.19: 以 / 开头的是选项开关，一律保留
        if p.startswith(chr(47)):
            new_parts.append(p)
        elif chr(58)+chr(47)+chr(47) in p:
            new_parts.append(p)
        else:
            new_parts.append(p.replace(chr(47), chr(92)))
    return chr(32).join(new_parts)


def _sync_run_command(cmd: str, timeout: int) -> tuple:
    cmd = _win_path_fix(cmd)
    start = datetime.datetime.now()
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, timeout=timeout
        )
        output = smart_decode(result.stdout or b"") + smart_decode(result.stderr or b"")
        status = "success" if result.returncode == 0 else "failed"
    except subprocess.TimeoutExpired:
        output, status = f"命令执行超时（>{timeout}秒）", "timeout"
    except Exception as e:
        output, status = f"命令执行异常: {e}", "error"

    if len(output) > MAX_OUTPUT_LENGTH:
        output = output[:MAX_OUTPUT_LENGTH] + f"\n... (已截断，原长 {len(output)} 字符)"

    dur = int((datetime.datetime.now() - start).total_seconds() * 1000)
    return output, status, dur


async def _run_command(cmd: str, timeout: int = DEFAULT_TIMEOUT) -> tuple:
    return await asyncio.to_thread(_sync_run_command, cmd, timeout)


# ========== Harness 调用 ==========

async def _run_harness(module_id: str, params: Dict[str, Any]) -> tuple:
    start = datetime.datetime.now()
    try:
        response = await asyncio.to_thread(harness_runtime.invoke_tool, module_id, params)
        dur = int((datetime.datetime.now() - start).total_seconds() * 1000)

        if not getattr(response, "success", False):
            error = getattr(response, "error", "未知错误")
            return f"Harness 失败: {error}", "failed", dur

        result = getattr(response, "result", None)
        if isinstance(result, dict):
            if result.get("success") is False:
                return f"Harness 失败: {result.get('error', '')}", "failed", dur
            output = result.get("text") or json.dumps(result, ensure_ascii=False)
            return output[:MAX_OUTPUT_LENGTH], "success", dur
        return str(result)[:MAX_OUTPUT_LENGTH], "success", dur
    except Exception as e:
        dur = int((datetime.datetime.now() - start).total_seconds() * 1000)
        return f"Harness 调用异常: {e}", "error", dur


# ========== 占位符替换 ==========

def _substitute_placeholders(cmd: str, previous_outputs: Dict[int, str]) -> str:
    if not previous_outputs:
        return cmd

    def replace_match(match):
        step_num = int(match.group(1))
        if step_num in previous_outputs:
            output = previous_outputs[step_num]
            for line in output.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.count("�") > 2:
                    continue
                if any(c in line for c in ["\\", "/", ":"]) and len(line) > 3:
                    return line
                return line
        return match.group(0)

    cmd = re.sub(r'\{\{step(\d+)\}\}', replace_match, cmd)
    cmd = re.sub(r'\{step(\d+)\}', replace_match, cmd)
    return cmd


def _substitute_params(params: Any, previous_outputs: Dict[int, str]) -> Any:
    """递归替换 params 里所有字符串值中的占位符"""
    if isinstance(params, dict):
        return {k: _substitute_params(v, previous_outputs) for k, v in params.items()}
    if isinstance(params, list):
        return [_substitute_params(v, previous_outputs) for v in params]
    if isinstance(params, str):
        return _substitute_placeholders(params, previous_outputs)
    return params


# ========== 汇报 ==========

async def _report_step_done(conversation_id: int, payload: Dict[str, Any], executor_id: str):
    """把 [STEP_DONE] 写入消息表，并触发审核"""
    content = "[STEP_DONE]:" + json.dumps(payload, ensure_ascii=False)
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, 'assistant', ?, ?)",
            (conversation_id, content, executor_id)
        )
        cur.execute(
            "UPDATE conversations SET updated_at=? WHERE id=?",
            (datetime.datetime.now().isoformat(), conversation_id)
        )
    await swarm_service.handle_step_done(conversation_id, payload, executor_id)


# ========== 任务执行 ==========

async def _execute_task(task: Dict[str, Any]):
    task_id = task["task_id"]
    conversation_id = task["conversation_id"]
    executor_id = task["executor_id"]
    steps = task.get("steps", [])
    done_set = set(task.get("done", set()))
    results = task.get("results", [])

    # 找未完成的步骤
    pending_steps = [s for s in steps if s.get("step") not in done_set]
    if not pending_steps:
        try:
            with db_cursor(commit=True) as _cur:
                _cur.execute("UPDATE swarm_pending_tasks SET status='completed' WHERE task_id=?", (task_id,))
            print(f"[executor] 任务 {task_id} 无待处理步骤，标记完成")
        except Exception as _e:
            print(f"[executor] 标记完成失败: {_e}")
        return

    # 从已有结果提取前序输出
    previous_outputs: Dict[int, str] = {}
    for r in results:
        if r.get("status") == "success":
            previous_outputs[r["step"]] = r.get("output", "")

    for step in pending_steps:
        output, status, dur = "", "error", 0
        # 每步执行前检查任务是否还在
        with db_cursor() as cur:
            cur.execute("SELECT cancelled FROM swarm_pending_tasks WHERE task_id=?", (task_id,))
            row = cur.fetchone()
            if not row:
                return  # 任务已完成或删除
            if row["cancelled"]:
                return

        step_id = step.get("step")
        desc = step.get("description", "")
        step_type = step.get("type", "command")

        print(f"[executor] task={task_id} step={step_id} type={step_type}")

        if step_type == "harness":
            module_id = step.get("module_id", "")
            params_raw = step.get("params", {})
            # 对 params 里所有字符串值做占位符替换
            params = _substitute_params(params_raw, previous_outputs)
            print(f"[executor]   harness params: {json.dumps(params, ensure_ascii=False)[:300]}")
            output, status, dur = await _run_harness(module_id, params)
            print(f"[executor]   harness 结果: {status} ({dur}ms) | {output[:200]}")
        else:
            cmd_raw = step.get("command", "")

            # 兼容 1：command 是 dict 且含 module_id → 转成 harness 调用
            if isinstance(cmd_raw, dict) and cmd_raw.get('module_id'):
                module_id = cmd_raw.get('module_id')
                params = _substitute_params(cmd_raw.get('params', {}), previous_outputs)
                print(f"[executor]   harness params (from dict): {json.dumps(params, ensure_ascii=False)[:300]}")
                output, status, dur = await _run_harness(module_id, params)
                print(f"[executor]   harness 结果: {status} ({dur}ms) | {output[:200]}")

            # 兼容 2：command 字符串含 "harness" 前缀 → 自动转成 harness 调用
            elif _looks_like_harness_prefix(cmd_raw):
                _raw = str(cmd_raw).strip()
                for _pfx in ('harness：', 'harness:', 'harness ', 'HARNESS：', 'HARNESS:', 'HARNESS '):
                    if _raw.startswith(_pfx):
                        _raw = _raw[len(_pfx):].strip()
                        break
                _parts = _raw.split(None, 1)
                _mid = _parts[0] if _parts else ''
                _params2 = {}
                if len(_parts) > 1:
                    _rest = _parts[1].strip()
                    try:
                        import json as _j_auto
                        _params2 = _j_auto.loads(_rest)
                    except Exception:
                        import re as _re_auto
                        for _kv in _re_auto.finditer(r'(\w+)\s*[=:]\s*["\']?([^"\'\s]+)["\']?', _rest):
                            _params2[_kv.group(1)] = _kv.group(2)
                _params2 = _substitute_params(_params2, previous_outputs)
                print(f"[executor]   harness params (auto): {json.dumps(_params2, ensure_ascii=False)[:300]}")
                output, status, dur = await _run_harness(_mid, _params2)
                print(f"[executor]   harness 结果 (auto): {status} ({dur}ms) | {output[:200]}")

            else:
                cmd = cmd_raw if isinstance(cmd_raw, str) else str(cmd_raw or "")
                for _k, _v in list(previous_outputs.items()):
                    _first_line = (_v or "").split(chr(10))[0].strip()
                    cmd = cmd.replace("{{step" + str(_k) + "}}", _first_line)
                    cmd = cmd.replace("{step" + str(_k) + "}", _first_line)
                cmd = cmd.strip()
                if cmd:
                    _timeout = step.get("timeout") or DEFAULT_TIMEOUT
                    output, status, dur = await _run_command(cmd, timeout=_timeout)
                    print(f"[executor]   command 结果: {status} ({dur}ms) | {output[:200]}")
                else:
                    output, status, dur = "空命令，跳过", "skipped", 0

        if status == "success":
            previous_outputs[step_id] = output

        payload = {
            "task_id": task_id,
            "step": step_id,
            "description": desc,
            "status": status,
            "output": output[:5000],
            "duration_ms": dur,
        }

        try:
            await _report_step_done(conversation_id, payload, executor_id)
        except Exception as e:
            print(f"[executor] 汇报失败: {e}")
            return


async def _execute_task_with_semaphore(task: Dict[str, Any]):
    task_id = task["task_id"]
    _running_task_ids.add(task_id)
    sem = _get_semaphore()
    async with sem:
        try:
            print(f"[executor] > 开始执行任务 {task_id}")
            await _execute_task(task)
            print(f"[executor] OK 任务 {task_id} 处理完毕")
        except Exception as e:
            import traceback
            print(f"[executor] X 任务 {task_id} 执行异常: {e}")
            traceback.print_exc()
        finally:
            _running_task_ids.discard(task_id)


# ========== 主循环 ==========

async def _scan_and_execute():
    """扫描数据库，执行所有待处理任务"""
    try:
        with db_cursor() as cur:
            cur.execute("""
                SELECT * FROM swarm_pending_tasks
                WHERE status IN ('pending', 'running')
                  AND cancelled = 0
                  AND is_draft = 0
                  AND no_plan = 0
                ORDER BY id ASC
                LIMIT 20
            """)
            rows = [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"[executor] 查询失败: {e}")
        return

    for row in rows:
        task_id = row["task_id"]
        if task_id in _running_task_ids:
            continue

        try:
            task = {
                "task_id": task_id,
                "conversation_id": row["conversation_id"],
                "user_id": row["user_id"],
                "commander_id": row["commander_id"],
                "executor_id": row["executor_id"],
                "user_text": row["user_text"] or "",
                "steps": json.loads(row["steps"] or "[]"),
                "results": json.loads(row["results"] or "[]"),
                "done": set(json.loads(row["done_steps"] or "[]")),
                "retry_count": row["retry_count"] or 0,
            }
        except Exception as e:
            print(f"[executor] 任务解析失败 {task_id}: {e}")
            continue

        asyncio.create_task(_execute_task_with_semaphore(task))


async def start_background_executor():
    """在 lifespan 中启动的后台任务"""
    print("[executor] 后台执行器启动")
    # 恢复未完成的任务
    try:
        swarm_service.restore_pending_tasks()
    except Exception as e:
        print(f"[executor] 恢复任务失败: {e}")

    while True:
        try:
            await _scan_and_execute()
        except Exception as e:
            print(f"[executor] 扫描异常: {e}")
        await asyncio.sleep(POLL_INTERVAL)
