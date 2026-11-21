# core/tool_sandbox.py
# -*- coding: utf-8 -*-
"""外部工具沙箱：子进程 + 超时 + 只读模块目录 + 仅 scratch 可写 + 禁网/禁子进程。

内置工具仍在进程内执行（性能优先）；只有 harness_modules/_external/* 走这里。
"""
import json
import os
import subprocess
import threading

_ACTIVE_PROCS = set()
_CANCEL = threading.Event()
_PROC_LOCK = threading.Lock()


def cancel_active():
    """P1-5: 取消当前所有沙箱子进程。"""
    _CANCEL.set()
    with _PROC_LOCK:
        procs = list(_ACTIVE_PROCS)
    for p in procs:
        try:
            p.kill()
        except Exception:
            pass
import sys
import tempfile
import time
from typing import Any, Optional, Tuple

RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tool_sandbox_runner.py")
_MARKER = "__SASES_RESULT__"
_MAX_RESULT_BYTES = 2 * 1024 * 1024
_DEFAULT_TIMEOUT = int(os.getenv("SASES_TOOL_TIMEOUT", "30"))


def _env() -> dict:
    keep = ("SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "NUMBER_OF_PROCESSORS")
    env = {k: v for k, v in os.environ.items() if k in keep}
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_external_tool(module_dir: str, entrypoint: str = "main.py",
                      params: Optional[dict] = None,
                      timeout: Optional[int] = None) -> Tuple[bool, Any, Optional[str], int]:
    """返回 (ok, result, error, duration_ms)。永不抛异常。"""
    start = time.time()
    timeout = int(timeout or _DEFAULT_TIMEOUT)
    try:
        if not module_dir or not os.path.isdir(module_dir):
            return False, None, "外部工具目录不存在: " + str(module_dir), 0
        if not os.path.isfile(os.path.join(module_dir, entrypoint)):
            return False, None, "入口文件不存在: " + str(entrypoint), 0

        with tempfile.TemporaryDirectory(prefix="sases_tool_") as _scratch:
            payload = json.dumps({
                "module_dir": os.path.abspath(module_dir),
                "entrypoint": entrypoint,
                "params": params or {},
                "scratch": _scratch,
            }, ensure_ascii=False)
            try:
                _CANCEL.clear()
                proc = subprocess.Popen(
                    [sys.executable, "-I", RUNNER],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=_scratch,
                    env=_env(),
                )
                with _PROC_LOCK:
                    _ACTIVE_PROCS.add(proc)
                try:
                    stdout_b, stderr_b = proc.communicate(payload.encode("utf-8"), timeout=timeout)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout_b, stderr_b = proc.communicate()
                    dur = int((time.time() - start) * 1000)
                    return False, None, "工具执行超时（>" + str(timeout) + " 秒），已终止", dur
                finally:
                    with _PROC_LOCK:
                        _ACTIVE_PROCS.discard(proc)
                if _CANCEL.is_set():
                    dur = int((time.time() - start) * 1000)
                    return False, None, "任务已取消，工具已终止", dur
            except Exception as _e_proc:
                return False, None, "沙箱启动失败: " + str(_e_proc), int((time.time() - start) * 1000)

            dur = int((time.time() - start) * 1000)
            stdout = (stdout_b or b"").decode("utf-8", "replace")
            stderr = (stderr_b or b"").decode("utf-8", "replace")
            line = ""
            for _line in stdout.splitlines():
                if _line.startswith(_MARKER):
                    line = _line[len(_MARKER):]
            if not line:
                return False, None, ("工具无有效输出（exit=" + str(proc.returncode) + "）"
                                     + ((" | stderr: " + stderr[-300:]) if stderr else "")), dur
            if len(line) > _MAX_RESULT_BYTES:
                return False, None, "工具返回结果过大（>" + str(_MAX_RESULT_BYTES) + " bytes）", dur
            try:
                data = json.loads(line)
            except Exception as e:
                return False, None, "工具返回格式非法: " + str(e), dur

            if data.get("ok"):
                return True, data.get("result"), None, dur
            return False, None, str(data.get("error") or "工具执行失败"), dur
    except Exception as e:
        return False, None, "沙箱异常: " + str(e), int((time.time() - start) * 1000)
