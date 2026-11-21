# core/services/artifact_service.py
# -*- coding: utf-8 -*-
"""测试快照 / 执行产物：落库 + 在聊天窗口回传（图片/文件气泡）+ WS 实时推送。

触发方式：
- 工具输出里出现 /static/... 的图片路径（verify_ui 截图等）
- 显式调用 record()
"""
import asyncio
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..db import db_cursor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATIC_DIR = os.path.join(ROOT, "static")

_ARTIFACT_RE = re.compile(
    r"(/static/(?:_ui_shots|generated|downloads)/[^\s\"'<>]+\.(?:png|jpe?g|webp|gif|pdf|zip|txt|log))",
    re.IGNORECASE,
)
_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def _kind_of(url: str) -> str:
    return "image" if url.lower().endswith(_IMAGE_EXT) else "file"


def _abs_path(url: str) -> Optional[str]:
    if not url.startswith("/static/"):
        return None
    p = os.path.abspath(os.path.join(ROOT, url.lstrip("/")))
    if not p.startswith(os.path.abspath(STATIC_DIR) + os.sep):
        return None
    return p


def _exists(run_id: int, path: str) -> bool:
    with db_cursor() as cur:
        cur.execute("SELECT 1 FROM run_artifacts WHERE run_id=? AND path=? LIMIT 1", (run_id, path))
        return cur.fetchone() is not None


def record(run_id: Optional[int], conversation_id: Optional[int], user_id: Optional[int],
           url: str, kind: Optional[str] = None, name: Optional[str] = None,
           meta: Optional[Dict[str, Any]] = None, silent: bool = False) -> Optional[Dict[str, Any]]:
    """记录一个产物；图片会同时插入一条 image 消息并在聊天窗展示。"""
    try:
        if not url or not url.startswith("/static/"):
            return None
        abs_p = _abs_path(url)
        if not abs_p or not os.path.isfile(abs_p):
            return None
        kind = kind or _kind_of(url)
        name = name or os.path.basename(abs_p)
        size = os.path.getsize(abs_p)
        if run_id and _exists(run_id, url):
            return None
        ts = datetime.utcnow().replace(microsecond=0).isoformat()
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO run_artifacts (run_id, conversation_id, kind, path, name, meta, created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (run_id, conversation_id, kind, url, name,
                 json.dumps(meta or {}, ensure_ascii=False), ts),
            )
            art_id = cur.lastrowid
            msg_id = None
            if conversation_id and not silent:
                att = [{"url": url, "name": name, "size": size, "type": kind}]
                content = ("[IMAGE]:" + url) if kind == "image" else ("[FILE]:" + name + "|" + str(size) + "|" + url)
                cur.execute(
                    "INSERT INTO messages (conversation_id, sender, content, msg_type, attachments) "
                    "VALUES (?, 'assistant', ?, ?, ?)",
                    (conversation_id, content, kind if kind == "image" else "file",
                     json.dumps(att, ensure_ascii=False)),
                )
                msg_id = cur.lastrowid
                cur.execute("UPDATE conversations SET updated_at=? WHERE id=?",
                            (datetime.now().isoformat(), conversation_id))
        if msg_id and user_id:
            try:
                from ..api_routes.ws_routes import broadcast_to_user
                asyncio.get_running_loop().create_task(broadcast_to_user(user_id, {
                    "type": "new_message",
                    "message_id": msg_id,
                    "conversation_id": conversation_id,
                    "sender": "assistant",
                    "content": ("[IMAGE]:" + url) if kind == "image" else ("[FILE]:" + name),
                    "msg_type": "image" if kind == "image" else "file",
                    "attachments": [{"url": url, "name": name, "size": size, "type": kind}],
                    "created_at": datetime.now().isoformat(),
                }))
            except RuntimeError:
                pass
            except Exception as e:
                print("[artifact] WS 推送失败: " + str(e))
        return {"id": art_id, "run_id": run_id, "path": url, "kind": kind, "name": name}
    except Exception as e:
        print("[artifact] record 失败: " + str(e))
        return None


def maybe_record_from_text(run_id: Optional[int], conversation_id: Optional[int],
                           user_id: Optional[int], text: Any,
                           meta: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """扫描工具输出里的 /static/... 产物路径并记录。"""
    if not run_id or text is None:
        return []
    s = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
    out = []
    seen = set()
    for m in _ARTIFACT_RE.finditer(s):
        url = m.group(1).rstrip(".,);]")
        if url in seen:
            continue
        seen.add(url)
        rec = record(run_id, conversation_id, user_id, url, meta=meta)
        if rec:
            out.append(rec)
    return out


def list_artifacts(run_id: int) -> List[Dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute("SELECT id, run_id, conversation_id, kind, path, name, meta, created_at "
                    "FROM run_artifacts WHERE run_id=? ORDER BY id ASC", (run_id,))
        return [dict(r) for r in cur.fetchall()]
