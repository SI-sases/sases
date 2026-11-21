# core/services/async_task_service.py
# -*- coding: utf-8 -*-
"""异步工具任务池：提交即返回 handle，poller 轮询进度，完成后回传聊天 + trace。"""
import asyncio
import importlib.util
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from ..db import db_cursor
from ..harness_models import ToolInvokeResponse

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODULES_DIR = os.path.join(ROOT, "harness_modules")
EXTERNAL_DIR = os.path.join(MODULES_DIR, "_external")

_ASYNC_CACHE: Dict[str, Optional[str]] = {}
_DEFAULT_TTL_MIN = 60


def _manifest_dirs():
    dirs = []
    if os.path.isdir(MODULES_DIR):
        for name in os.listdir(MODULES_DIR):
            p = os.path.join(MODULES_DIR, name)
            if name.startswith("_") or not os.path.isdir(p):
                continue
            dirs.append(p)
    if os.path.isdir(EXTERNAL_DIR):
        for name in os.listdir(EXTERNAL_DIR):
            p = os.path.join(EXTERNAL_DIR, name)
            if os.path.isdir(p):
                dirs.append(p)
    return dirs


def _manifest(tool_id: str) -> Optional[dict]:
    for d in _manifest_dirs():
        mp = os.path.join(d, "manifest.json")
        if not os.path.exists(mp):
            continue
        try:
            with open(mp, "r", encoding="utf-8") as f:
                data = json.load(f)
            if str(data.get("id")) == str(tool_id):
                data["__dir"] = d
                return data
        except Exception:
            continue
    return None


def is_async_tool(tool_id: str) -> bool:
    if tool_id in _ASYNC_CACHE:
        return bool(_ASYNC_CACHE[tool_id])
    m = _manifest(tool_id)
    mode = (m or {}).get("task_mode")
    _ASYNC_CACHE[tool_id] = mode if mode == "async" else None
    return mode == "async"


def _load_poll(tool_id: str):
    m = _manifest(tool_id)
    if not m:
        return None
    entry = m.get("entrypoint") or "main.py"
    path = os.path.join(m["__dir"], entry)
    try:
        spec = importlib.util.spec_from_file_location("async_tool_" + str(tool_id), path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return getattr(mod, "poll", None)
    except Exception as e:
        print("[async] load poll failed " + str(tool_id) + ": " + str(e))
        return None


def submit(tool_id: str, params: Dict[str, Any], run_id=None, conversation_id=None,
           user_id=None) -> ToolInvokeResponse:
    try:
        from core.harness_runtime import harness_runtime
        resp = harness_runtime.invoke_tool(tool_id, params)
        if not getattr(resp, "success", False):
            return resp
        result = getattr(resp, "result", None) or {}
        handle = result.get("handle") or result.get("task_handle")
        if not handle:
            return ToolInvokeResponse(module_id=tool_id, success=False,
                                      error="异步工具未返回 handle")
        now = datetime.now()
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT OR REPLACE INTO async_task_pool "
                "(handle, tool_id, params, status, progress, run_id, conversation_id, user_id, "
                " created_at, updated_at, expires_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (str(handle), tool_id, json.dumps(params or {}, ensure_ascii=False), "submitted", 0,
                 run_id, conversation_id, user_id, now.isoformat(), now.isoformat(),
                 (now + timedelta(minutes=_DEFAULT_TTL_MIN)).isoformat()),
            )
        print("[async] submitted " + tool_id + " handle=" + str(handle))
        return ToolInvokeResponse(module_id=tool_id, success=True,
                                  result={"status": "submitted", "handle": str(handle), "tool_id": tool_id})
    except Exception as e:
        return ToolInvokeResponse(module_id=tool_id, success=False, error="async submit 失败: " + str(e))


def attach(handle: str, run_id=None, conversation_id=None, user_id=None, tool_id=None):
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE async_task_pool SET run_id=COALESCE(?,run_id), "
                "conversation_id=COALESCE(?,conversation_id), user_id=COALESCE(?,user_id), "
                "tool_id=COALESCE(?,tool_id), updated_at=? WHERE handle=?",
                (run_id, conversation_id, user_id, tool_id, datetime.now().isoformat(), str(handle)),
            )
    except Exception as e:
        print("[async] attach 失败: " + str(e))


def get_by_handle(handle: str) -> Optional[dict]:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM async_task_pool WHERE handle=?", (str(handle),))
        r = cur.fetchone()
        return dict(r) if r else None


def poll_pending() -> int:
    try:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM async_task_pool WHERE status IN ('submitted','running') "
                        "ORDER BY id ASC LIMIT 20")
            rows = [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print("[async] 查询池失败: " + str(e))
        return 0

    done = 0
    for row in rows:
        handle = row["handle"]
        tool_id = row["tool_id"]
        try:
            if row.get("expires_at") and datetime.fromisoformat(row["expires_at"]) < datetime.now():
                _finish(row, "failed", error="异步任务超时")
                done += 1
                continue
            poll = _load_poll(tool_id)
            if not poll:
                continue
            info = poll(handle) or {}
            state = str(info.get("state") or "running")
            progress = int(info.get("progress") or 0)
            if state == "done" or state == "succeeded":
                _finish(row, "succeeded", result=info.get("result"))
                done += 1
            elif state in ("failed", "error"):
                _finish(row, "failed", error=str(info.get("error") or "failed"))
                done += 1
            else:
                with db_cursor(commit=True) as cur:
                    cur.execute("UPDATE async_task_pool SET status='running', progress=?, updated_at=? WHERE handle=?",
                                (progress, datetime.now().isoformat(), handle))
        except Exception as e:
            print("[async] poll " + str(tool_id) + " 失败: " + str(e))
    return done


def _finish(row: dict, status: str, result=None, error=None):
    now = datetime.now().isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE async_task_pool SET status=?, progress=100, result=?, error=?, "
                    "updated_at=?, finished_at=? WHERE handle=? AND status IN ('submitted','running')",
                    (status, json.dumps(result, ensure_ascii=False) if result is not None else None,
                     error, now, now, row["handle"]))
        if cur.rowcount == 0:
            return
    try:
        if row.get("run_id"):
            from . import trace_service
            text = ("异步任务完成：" + str(result)[:300]) if status == "succeeded" else ("异步任务失败：" + str(error))
            trace_service.emit(row["run_id"], row.get("conversation_id"), 2, "async_done",
                               content=text, tool=row.get("tool_id"), status=status)
    except Exception as e:
        print("[async] trace 写入失败: " + str(e))
    try:
        if row.get("conversation_id") and row.get("user_id"):
            _notify_chat(row, status, result, error)
    except Exception as e:
        print("[async] 通知失败: " + str(e))


def _notify_chat(row, status, result, error):
    cid = row["conversation_id"]
    uid = row["user_id"]
    text = ("⏱ 异步任务完成：" + str(result)[:500]) if status == "succeeded" else ("⏱ 异步任务失败：" + str(error)[:300])
    with db_cursor(commit=True) as cur:
        cur.execute("INSERT INTO messages (conversation_id, sender, content) VALUES (?, 'assistant', ?)",
                    (cid, "[SUMMARY]:" + text))
        msg_id = cur.lastrowid
    try:
        from ..api_routes.ws_routes import broadcast_to_user
        asyncio.get_running_loop().create_task(broadcast_to_user(uid, {
            "type": "new_message", "message_id": msg_id, "conversation_id": cid,
            "sender": "assistant", "content": "[SUMMARY]:" + text,
        }))
    except Exception:
        pass


async def poller_loop(interval: int = 3):
    print("[async] poller started, interval=" + str(interval) + "s")
    while True:
        try:
            n = await asyncio.to_thread(poll_pending)
            if n:
                print("[async] 本轮完成 " + str(n) + " 个异步任务")
        except Exception as e:
            print("[async] poller 异常: " + str(e))
        await asyncio.sleep(interval)
