# core/services/checkpoint_service.py
# -*- coding: utf-8 -*-
"""P2-2: 写文件前做检查点，支持按 run 一键回滚。"""
import hashlib
import os
import shutil
from datetime import datetime

from ..db import db_cursor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CKPT_DIR = os.path.join(ROOT, ".checkpoints")


def _rel(path: str):
    p = str(path or "").replace("\\", "/").strip()
    if not p or p.startswith("/") or (len(p) > 1 and p[1] == ":") or ".." in p.split("/"):
        return None
    return p


def _abs(rel: str) -> str:
    return os.path.join(ROOT, rel.replace("/", os.sep))


def _sha(path: str):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(run_id, step_id, rel_path):
    """写前记录；文件不存在记录 sha=None（回滚时删除）。"""
    if not run_id:
        return
    rel = _rel(rel_path)
    if not rel:
        return
    ab = _abs(rel)
    sha = None
    backup = None
    try:
        if os.path.isfile(ab):
            sha = _sha(ab)
            d = os.path.join(CKPT_DIR, str(run_id))
            os.makedirs(d, exist_ok=True)
            name = rel.replace("/", "__") + "." + datetime.now().strftime("%H%M%S_%f") + ".bak"
            backup = os.path.join(d, name)
            shutil.copy2(ab, backup)
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT OR IGNORE INTO file_checkpoints (run_id, step_id, path, backup_path, sha_before, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (int(run_id), str(step_id or ""), rel, backup, sha, datetime.utcnow().replace(microsecond=0).isoformat()),
            )
    except Exception as e:
        print("[checkpoint] snapshot 失败: " + str(e))


def revert(run_id):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM file_checkpoints WHERE run_id=? ORDER BY id DESC", (int(run_id),))
        rows = [dict(r) for r in cur.fetchall()]
    restored, deleted, failed = [], [], []
    for r in rows:
        rel = r.get("path")
        ab = _abs(rel) if rel else None
        try:
            if r.get("sha_before") is None:
                if ab and os.path.isfile(ab):
                    os.remove(ab)
                deleted.append(rel)
            elif r.get("backup_path") and os.path.isfile(r["backup_path"]):
                os.makedirs(os.path.dirname(ab) or ".", exist_ok=True)
                shutil.copy2(r["backup_path"], ab)
                restored.append(rel)
            else:
                failed.append({"path": rel, "reason": "backup missing"})
        except Exception as e:
            failed.append({"path": rel, "reason": str(e)})
    return {"restored": restored, "deleted": deleted, "failed": failed, "total": len(rows)}
