import os, sys
# SASES_PATH_INJECT
_py_dir = os.path.dirname(sys.executable)
_git_bin = r"C:\\Program Files\\Git\\usr\\bin"
_git_cmd = r"C:\\Program Files\\Git\\cmd"
_env_path = os.environ.get("PATH", "")
if _py_dir not in _env_path:
    _env_path = _py_dir + os.pathsep + _env_path
if _git_bin not in _env_path:
    _env_path = _git_bin + os.pathsep + _env_path
if _git_cmd not in _env_path:
    _env_path = _git_cmd + os.pathsep + _env_path
os.environ["PATH"] = _env_path

import sys
import os

_py_dir = os.path.dirname(sys.executable)
if _py_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _py_dir + os.pathsep + os.environ.get("PATH", "")

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
from .. import tool_gateway


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
DEFAULT_TIMEOUT = 30
STEP_TIMEOUT = 180
_SIDE_EFFECT = {"file_write", "smart_edit", "file_replace_range", "delete_block", "split_block", "git_ops", "http_async"}


def _idem_put(module_id: str, key, output):
    if not key or module_id not in _SIDE_EFFECT:
        return
    try:
        from . import run_journal as _rj_i
        _rj_i.effect_put(str(key), module_id, str(output)[:20000])
    except Exception as _e_i:
        print("[idempotent] 写入失败: " + str(_e_i))


def _spill_large(output, run_id=None, conversation_id=None, user_id=None, module_id="tool"):
    """P1-3: 超过 MAX_OUTPUT_LENGTH 的输出落 artifact，返回截断文本 + 指针。"""
    text = str(output or "")
    if len(text) <= MAX_OUTPUT_LENGTH:
        return text
    try:
        import time as _time_sp
        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        _dir = os.path.join(_root, "static", "generated")
        os.makedirs(_dir, exist_ok=True)
        _name = "tool_output_" + str(run_id or 0) + "_" + str(int(_time_sp.time() * 1000)) + ".txt"
        _path = os.path.join(_dir, _name)
        with open(_path, "w", encoding="utf-8") as f:
            f.write(text)
        _url = "/static/generated/" + _name
        try:
            from . import artifact_service
            artifact_service.record(run_id, conversation_id, user_id, _url,
                                    kind="file", name=_name,
                                    meta={"tool": module_id, "kind": "tool_output"}, silent=True)
        except Exception as _e_ar:
            print("[artifact] 记录大输出失败: " + str(_e_ar))
        print("[artifact] 大输出已落盘 " + _url + " (" + str(len(text)) + " chars)")
        return text[:MAX_OUTPUT_LENGTH] + "\n...[已截断，完整输出: " + _url + "]"
    except Exception as e:
        print("[artifact] 大输出落盘失败: " + str(e))
        return text[:MAX_OUTPUT_LENGTH]
POLL_INTERVAL = 3
MAX_CONCURRENT_TASKS = 3

# ========== 内存状态 ==========

_running_task_ids: set = set()
_paused_logged: set = set()
_global_semaphore: Optional[asyncio.Semaphore] = None




# P2A2: 物理拦截 file_read JSON 污染 old_code
def _check_old_code_pollution(module_id, params):
    """检测 old_code/old_snippet/old_content 是否被 file_read JSON 污染"""
    if not isinstance(params, dict):
        return None
    for key in ("old_code", "old_snippet", "old_content", "new_code", "new_content", "content"):
        v = params.get(key)
        if isinstance(v, str):
            sv = v.strip()
            if sv.startswith('{"success"') or sv.startswith("{'success'"):
                return {
                    "success": False,
                    "error": (
                        "参数 " + key + " 看起来是 file_read 的 JSON 返回值。"
                        "请先提取 content 字段后再传给 " + str(module_id)
                    )
                }
    return None


# ========== 跨轮熔断 + 等价工具降级（v0.46） ==========

_CIRCUIT_DB_WINDOW_MIN = 30
_CIRCUIT_TASK_THRESHOLD = 3
_task_fail_counts: Dict[tuple, int] = {}


def _db_circuit_check(module_id: str, user_id=None) -> Optional[str]:
    """跨轮熔断继承：读 safety_memory 里 30 分钟内的熔断记录。

    注意：safety_memory.created_at 存在 UTC/local 混用，不能用来排序或算时效，
    因此按 id 倒序取最近记录，并用 content 里的 [ts=epoch] 判断新鲜度。
    """
    if not user_id:
        return None
    try:
        import re as _re_c
        import time as _time_c
        with db_cursor() as _cur_c:
            _cur_c.execute(
                "SELECT content FROM safety_memory WHERE user_id=? AND memory_type='failure_pattern' "
                "ORDER BY id DESC LIMIT 20",
                (user_id,),
            )
            _rows_c = _cur_c.fetchall()
        for _row_c in _rows_c:
            txt = str((_row_c["content"] if isinstance(_row_c, dict) else _row_c[0]) or "")
            if module_id not in txt or "熔断" not in txt:
                continue
            _m = _re_c.search(r"\[ts=(\d+)\]", txt)
            if not _m:
                continue
            if _time_c.time() - int(_m.group(1)) > _CIRCUIT_DB_WINDOW_MIN * 60:
                continue
            print("[executor] 跨轮熔断继承命中: " + module_id)
            return ("Error: " + module_id + " 近期熔断（" + txt[:100]
                    + "），本轮改用等价工具")
    except Exception as e:
        print("[executor] 跨轮熔断检查失败: " + str(e))
    return None


def _db_circuit_record(module_id: str, user_id, task_id, error) -> None:
    """同一任务内同一工具连续失败 N 次 -> 写一条跨轮熔断记录。"""
    key = (str(task_id), module_id)
    n = _task_fail_counts.get(key, 0) + 1
    _task_fail_counts[key] = n
    if n < _CIRCUIT_TASK_THRESHOLD or not user_id:
        return
    try:
        import time as _time_w
        from . import memory_service
        memory_service.remember(
            user_id=user_id,
            memory_type="failure_pattern",
            content=(module_id + " 熔断（连续 " + str(n) + " 次失败）：" + str(error or "")[:150]
                     + " [ts=" + str(int(_time_w.time())) + "]"),
            task_id=str(task_id),
            importance=0.6,
            tags="failure,circuit",
            enable_dedup=False,
        )
        print("[executor] 熔断记录已写入: " + module_id + " x" + str(n))
    except Exception as e:
        print("[executor] 熔断记录写入失败: " + str(e))


def _grep_fallback_code(params: Dict[str, Any]) -> Optional[str]:
    """把 grep_code 参数翻译成 run_python 扫描脚本（等价降级）。"""
    try:
        pattern = str(params.get("pattern") or "").strip()
        if not pattern:
            return None
        path = str(params.get("path") or ".").strip() or "."
        ext = str(params.get("file_ext") or "").strip()
        max_results = int(params.get("max_results") or 30)
        max_results = max(1, min(max_results, 100))
        template = """import os,re,json
pat=%r
root=%r
ext=%r
cap=%d
out=[]
for dp,dn,fn in os.walk(root):
    dn[:]=[d for d in dn if d not in ('.git','__pycache__','venv','venv312','node_modules','.backups','archive')]
    for f in fn:
        if ext and not f.endswith(ext):
            continue
        if f.endswith(('.bak','.pyc','.log','.tmp')):
            continue
        p=os.path.normpath(os.path.join(dp,f)).replace(chr(92),'/')
        try:
            lines=open(p,encoding='utf-8',errors='replace').read().splitlines()
        except Exception:
            continue
        for i,l in enumerate(lines,1):
            try:
                hit=(re.search(pat,l) is not None)
            except re.error:
                hit=(pat in l)
            if hit:
                out.append({'file':p,'line':i,'text':l.rstrip()[:200]})
                if len(out)>=cap:
                    break
        if len(out)>=cap:
            break
    if len(out)>=cap:
        break
print(json.dumps({'success':True,'pattern':pat,'count':len(out),'matches':out},ensure_ascii=False))
"""
        return template % (pattern, path, ext, max_results)
    except Exception as e:
        print("[executor] grep 降级脚本生成失败: " + str(e))
        return None


async def _try_equivalent_tool(module_id: str, params: Dict[str, Any]):
    """工具失败后尝试等价工具；成功返回 (output, status, dur)。"""
    if module_id != "grep_code":
        return None
    code = _grep_fallback_code(params)
    if not code:
        return None
    try:
        resp = await tool_gateway.invoke_tool_async("run_python", {"code": code})
        if not getattr(resp, "success", False):
            return None
        r = getattr(resp, "result", None)
        if not isinstance(r, dict) or r.get("success") is False:
            return None
        out = r.get("stdout") or r.get("text") or ""
        if not str(out).strip():
            return None
        print("[executor] grep_code 失败，已降级 run_python 扫描成功")
        return "[fallback:run_python] " + str(out)[:MAX_OUTPUT_LENGTH], "success", 0
    except Exception as e:
        print("[executor] 等价工具降级异常: " + str(e))
        return None


def _render_step_display(step: Dict[str, Any], output: str) -> str:
    try:
        from .swarm.tool_render import render_tool_text
        return render_tool_text(str(step.get("module_id") or ""), output or "")
    except Exception:
        return str(output or "")[:300]


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
            cmd, shell=True, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL
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

async def _run_harness(module_id: str, params: Dict[str, Any], user_id=None, task_id=None, idem_key=None,
                       conversation_id=None, run_id=None) -> tuple:
    start = datetime.datetime.now()
    try:
        # P0-3: 副作用幂等（重试/重复派发复用上次结果）
        if idem_key and module_id in _SIDE_EFFECT:
            try:
                from . import run_journal as _rj_fx
                _hit = _rj_fx.effect_get(idem_key)
                if _hit is not None:
                    dur = int((datetime.datetime.now() - start).total_seconds() * 1000)
                    print("[idempotent] 命中 " + str(idem_key) + " tool=" + module_id)
                    return "[idempotent] " + str(_hit)[:MAX_OUTPUT_LENGTH], "success", dur
            except Exception as _e_fx:
                print("[idempotent] 查询失败: " + str(_e_fx))

        # v0.46: 跨轮熔断继承（先于实际调用）
        _blocked = _db_circuit_check(module_id, user_id)
        if _blocked:
            dur = int((datetime.datetime.now() - start).total_seconds() * 1000)
            return _blocked, "failed", dur

        # P2A2: 拦截 old_code 被 file_read JSON 污染
        _pollution = _check_old_code_pollution(module_id, params)
        if _pollution:
            dur = int((datetime.datetime.now() - start).total_seconds() * 1000)
            _db_circuit_record(module_id, user_id, task_id, _pollution["error"])
            return f"Harness 失败: {_pollution['error']}", "failed", dur

        # P1: 把 run_id 注入参数，供工具做先读后写/观测
        if idem_key:
            _rid_s = str(idem_key).split(":")[0]
            if _rid_s.isdigit():
                params = dict(params or {})
                params.setdefault("_run_id", int(_rid_s))

        try:
            response = await asyncio.wait_for(
                tool_gateway.invoke_tool_async(module_id, params),
                timeout=STEP_TIMEOUT,
            )
        except asyncio.TimeoutError:
            dur = int((datetime.datetime.now() - start).total_seconds() * 1000)
            _db_circuit_record(module_id, user_id, task_id, "timeout")
            return "工具执行超时(" + str(STEP_TIMEOUT) + "s)", "timeout", dur
        dur = int((datetime.datetime.now() - start).total_seconds() * 1000)

        if not getattr(response, "success", False):
            error = getattr(response, "error", "未知错误")
            _db_circuit_record(module_id, user_id, task_id, error)
            _fb = await _try_equivalent_tool(module_id, params)
            if _fb:
                return _fb
            return f"Harness 失败: {error}", "failed", dur

        result = getattr(response, "result", None)
        if isinstance(result, dict):
            if result.get("success") is False:
                _err_r = result.get("error", "")
                _db_circuit_record(module_id, user_id, task_id, _err_r)
                _fb = await _try_equivalent_tool(module_id, params)
                if _fb:
                    return _fb
                return f"Harness 失败: {_err_r}", "failed", dur
            output = result.get("text") or result.get("stdout") or json.dumps(result, ensure_ascii=False)
            _task_fail_counts.pop((str(task_id), module_id), None)
            _idem_put(module_id, idem_key, output)
            output = _spill_large(output, run_id, conversation_id, user_id, module_id)
            return output[:MAX_OUTPUT_LENGTH], "success", dur
        _task_fail_counts.pop((str(task_id), module_id), None)
        _idem_put(module_id, idem_key, result)
        _out_str = _spill_large(str(result), run_id, conversation_id, user_id, module_id)
        return _out_str[:MAX_OUTPUT_LENGTH], "success", dur
    except Exception as e:
        dur = int((datetime.datetime.now() - start).total_seconds() * 1000)
        return f"Harness 调用异常: {e}", "error", dur


# ========== 占位符替换 ==========

def _substitute_placeholders(cmd: str, previous_outputs: Dict[int, str]) -> str:
    if not previous_outputs:
        return cmd

    def replace_match(match):
        step_num = int(match.group(1))
        field = match.group(2) if match.re.groups >= 2 else None
        if field and step_num in previous_outputs:
            try:
                import json as _json_ph
                _raw = previous_outputs[step_num]
                data = _json_ph.loads(_raw) if isinstance(_raw, str) else _raw
                if isinstance(data, dict) and field in data:
                    return str(data[field])
            except Exception:
                pass
            return match.group(0)
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

    cmd = re.sub(r'\{\{step(\d+)(?:\.([A-Za-z_][A-Za-z0-9_]*))?\}\}', replace_match, cmd)
    cmd = re.sub(r'\{step(\d+)(?:\.([A-Za-z_][A-Za-z0-9_]*))?\}', replace_match, cmd)
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

    # P0: 租约 + 断点恢复
    _run_id = task.get("supervisor_run_id")
    _owner = "exec:%s:%s" % (os.getpid(), task_id)
    _rj = None
    if _run_id:
        try:
            from . import run_journal as _rj
            if not _rj.acquire_lease(_run_id, _owner):
                print("[journal] run " + str(_run_id) + " 已被其他执行器持有，跳过")
                return
            _rj.set_deadline(_run_id, 1800)
            _done_j = _rj.done_step_ids(_run_id)
            if _done_j:
                for _x in _done_j:
                    try:
                        done_set.add(int(_x))
                    except Exception:
                        done_set.add(_x)
                print("[journal] run " + str(_run_id) + " 断点恢复，已完成 " + str(len(_done_j)) + " 步")
        except Exception as _e_j:
            print("[journal] 租约/恢复失败: " + str(_e_j))
            _rj = None

    # 找未完成的步骤
    pending_steps = [s for s in steps if isinstance(s, dict) and s.get("step") not in done_set]
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
        # P1-A2: 暂停/取消检查（每步开始前）
        _run_state = None
        try:
            with db_cursor() as _cur_pause:
                _cur_pause.execute("SELECT status FROM supervisor_runs WHERE id=?", (task.get("supervisor_run_id"),))
                _row_pause = _cur_pause.fetchone()
            if _row_pause:
                _run_state = _row_pause["status"] if isinstance(_row_pause, dict) else _row_pause[0]
        except Exception as _e_pause:
            print("[executor] pause check failed: " + str(_e_pause))
        if _run_state in ("paused", "cancelled", "interrupted"):
            if task_id not in _paused_logged:
                _paused_logged.add(task_id)
                print("[executor] run " + str(task.get("supervisor_run_id")) + " 状态=" + str(_run_state) + "，任务暂停，step " + str(step.get("step")) + " 未执行")
            return
        _paused_logged.discard(task_id)
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
        step_type = "command" if str(step.get("command") or "").strip() else ("harness" if step.get("module_id") else step.get("type", "command"))

        # P0: 截止时间 + 心跳 + 步骤日志
        if _run_id and _rj:
            try:
                if _rj.deadline_expired(_run_id):
                    print("[journal] run " + str(_run_id) + " 超过 deadline，终止")
                    with db_cursor(commit=True) as _c_dl:
                        _c_dl.execute("UPDATE supervisor_runs SET status='timeout', finished_at=datetime('now') WHERE id=?", (_run_id,))
                    return
                _rj.heartbeat(_run_id, _owner)
                _rj.step_begin(_run_id, str(step_id), str(step.get("module_id") or step.get("command") or ""),
                               _owner, key=str(_run_id) + ":" + str(step_id))
            except Exception as _e_j2:
                print("[journal] step_begin 失败: " + str(_e_j2))

        # run_trace: 步骤开始（失败不影响执行）
        try:
            from . import trace_service as _trace_svc
            _trace_svc.emit(
                task.get("supervisor_run_id"), conversation_id, 2, "step_start",
                content="步骤 " + str(step_id) + "：" + str(desc)[:120],
                tool=str(step.get("module_id") or step.get("command") or "")[:80],
                status="running",
            )
        except Exception as _e_tr:
            print("[trace] step_start 写入失败: " + str(_e_tr))

        print(f"[executor] task={task_id} step={step_id} type={step_type}")

        if step_type == "harness":
            module_id = step.get("module_id", "")
            params_raw = step.get("params", {})
            # 对 params 里所有字符串值做占位符替换
            params = _substitute_params(params_raw, previous_outputs)
            print(f"[executor]   harness params: {json.dumps(params, ensure_ascii=False)[:300]}")
            output, status, dur = await _run_harness(module_id, params, task.get("user_id"), task_id,
                                                     idem_key=(str(_run_id) + ":" + str(step_id)) if _run_id else None,
                                                     conversation_id=conversation_id, run_id=_run_id)
            print(f"[executor]   harness 结果: {status} ({dur}ms) | {output[:200]}")
        else:
            cmd_raw = step.get("command", "")

            # 兼容 1：command 是 dict 且含 module_id → 转成 harness 调用
            if isinstance(cmd_raw, dict) and cmd_raw.get('module_id'):
                module_id = cmd_raw.get('module_id')
                params = _substitute_params(cmd_raw.get('params', {}), previous_outputs)
                print(f"[executor]   harness params (from dict): {json.dumps(params, ensure_ascii=False)[:300]}")
                output, status, dur = await _run_harness(module_id, params, task.get("user_id"), task_id,
                                                     idem_key=(str(_run_id) + ":" + str(step_id)) if _run_id else None,
                                                     conversation_id=conversation_id, run_id=_run_id)
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
                output, status, dur = await _run_harness(_mid, _params2, task.get("user_id"), task_id,
                                                         idem_key=(str(_run_id) + ":" + str(step_id)) if _run_id else None,
                                                         conversation_id=conversation_id, run_id=_run_id)
                print(f"[executor]   harness 结果 (auto): {status} ({dur}ms) | {output[:200]}")

            else:
                cmd = cmd_raw if isinstance(cmd_raw, str) else str(cmd_raw or "")
                for _k, _v in list(previous_outputs.items()):
                    _first_line = (_v or "").split(chr(10))[0].strip()
                    cmd = cmd.replace("{{step" + str(_k) + "}}", _first_line)
                    cmd = cmd.replace("{step" + str(_k) + "}", _first_line)
                cmd = cmd.strip()
                if cmd:
                    # v2.7.0: 检测 command 首个词是否为 harness 工具别名
                    _first_word = cmd.split(None, 1)[0].lower() if cmd else ""
                    _alias_map = {
                        "file_write": "file_write",
                        "write_file": "file_write",
                        "fs_create": "file_write",
                        "create_file": "file_write",
                        "save_file": "file_write",
                        "edit_file": "file_write",
                        "read_file": "file_read",
                        "search_text": "grep_code",
                        "list_files": "dir_tree",
                        "run_script": "run_python",
                        "call_api": "api_call",
                        "read_url": "web_fetch",
                    }
                    if _first_word in _alias_map:
                        _correct = _alias_map[_first_word]
                        output = (
                            f"检测到工具别名 '{_first_word}' 被误用作 shell 命令。"
                            f"正确做法：type=harness, module_id={_correct}, "
                            f"params 里传 file_path / new_content 等。"
                        )
                        status, dur = "failed", 0
                        print(f"[executor]   command 是工具别名，拒绝执行: {_first_word} → 建议 {_correct}")
                    else:
                        _timeout = step.get("timeout") or DEFAULT_TIMEOUT
                        output, status, dur = await _run_command(cmd, timeout=_timeout)
                        print(f"[executor]   command 结果: {status} ({dur}ms) | {output[:200]}")
                else:
                    output, status, dur = "空命令，跳过", "skipped", 0

        if status == "success":
            previous_outputs[step_id] = output

        # 异步工具：把 handle 绑定回本次 run/会话，poller 完成后回传
        try:
            import json as _json_as
            _ad = _json_as.loads(output) if isinstance(output, str) and output.strip().startswith("{") else None
            if isinstance(_ad, dict) and _ad.get("status") == "submitted" and _ad.get("handle"):
                from . import async_task_service as _ats
                _ats.attach(_ad["handle"], task.get("supervisor_run_id"), conversation_id,
                            task.get("user_id"), _ad.get("tool_id"))
        except Exception as _e_as:
            print("[async] attach 失败: " + str(_e_as))

        payload = {
            "task_id": task_id,
            "step": step_id,
            "description": desc,
            "status": status,
            "output": output[:5000],
            "display": _render_step_display(step, output),
            "duration_ms": dur,
        }

        # P0: 步骤结果落日志
        if _run_id and _rj:
            try:
                _rj.step_end(_run_id, str(step_id), status,
                             error=None if status == "success" else str(output)[:300])
            except Exception as _e_j3:
                print("[journal] step_end 失败: " + str(_e_j3))

        try:
            await _report_step_done(conversation_id, payload, executor_id)
        except Exception as e:
            print(f"[executor] 汇报失败: {e}")
            return

        # run_trace: 步骤结果（先落库，再 WS 推送）
        _trace_seq = 0
        try:
            from . import trace_service as _trace_svc
            _ev = _trace_svc.emit(
                task.get("supervisor_run_id"), conversation_id, 2, "step_done",
                content=str(payload.get("display") or output or "")[:1000],
                tool=str(step.get("module_id") or step.get("command") or "")[:80],
                status=status, duration_ms=dur,
            )
            _trace_seq = _ev.get("seq", 0)
        except Exception as _e_tr:
            print("[trace] step_done 写入失败: " + str(_e_tr))

        # 测试快照：工具输出里的 /static/... 产物回传聊天窗口
        try:
            from . import artifact_service as _art_svc
            _art_svc.maybe_record_from_text(
                task.get("supervisor_run_id"), conversation_id, task.get("user_id"),
                output, meta={"step": step_id, "tool": str(step.get("module_id") or "")[:60]},
            )
        except Exception as _e_art:
            print("[artifact] 回传失败: " + str(_e_art))

        # P3-C3: 每步推送 trace 到子窗口
        try:
            from ..broadcast.ws_hub import broadcast_to_user as _btu_c3
            await _btu_c3(task.get("user_id"), {
                "type": "task_trace",
                "run_id": task.get("supervisor_run_id"),
                "conversation_id": conversation_id,
                "task_id": task_id,
                "seq": _trace_seq,
                "level": 2,
                "event_type": "step_done",
                "step": step_id,
                "total": len(task.get("steps") or []),
                "tool": str(step.get("module_id") or step.get("command") or "")[:100],
                "status": status,
                "duration_ms": dur,
                "output_preview": str(payload.get("display") or output or "")[:200],
            })
        except Exception as _e_c3:
            print("[P3-C3] trace WS 推送失败: " + str(_e_c3))


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
            # P0-4: 任务结束释放租约
            try:
                from . import run_journal as _rj_rel
                _rid_rel = task.get("supervisor_run_id")
                if _rid_rel:
                    _rj_rel.release(_rid_rel, "exec:%s:%s" % (os.getpid(), task_id))
            except Exception as _e_rel:
                print("[journal] 释放租约失败: " + str(_e_rel))


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
                "supervisor_run_id": row.get("supervisor_run_id"),
                "user_text": row["user_text"] or "",
                "steps": json.loads(row["steps"] or "[]"),
                "results": json.loads(row["results"] or "[]"),
                "done": set(json.loads(row["done_steps"] or "[]")),
                "retry_count": row["retry_count"] or 0,
            }
        except Exception as e:
            print(f"[executor] 任务解析失败 {task_id}: {e}")
            continue

        # P1-A2: paused run 不派发，避免每 3 秒空转
        try:
            _rid_scan = row.get("supervisor_run_id")
            if _rid_scan:
                with db_cursor() as _c_scan:
                    _c_scan.execute("SELECT status FROM supervisor_runs WHERE id=?", (_rid_scan,))
                    _r_scan = _c_scan.fetchone()
                _st_scan = (_r_scan["status"] if isinstance(_r_scan, dict) else _r_scan[0]) if _r_scan else None
                if _st_scan == "paused":
                    continue
        except Exception as _e_scan:
            print("[executor] scan pause check failed: " + str(_e_scan))

        asyncio.create_task(_execute_task_with_semaphore(task))


async def start_background_executor():
    """在 lifespan 中启动的后台任务"""
    print("[executor] 后台执行器启动")
    # P0: 回收过期步骤
    try:
        from . import run_journal as _rj_boot
        _rj_boot.recover_stale()
    except Exception as _e_rj:
        print("[journal] 启动回收失败: " + str(_e_rj))
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
