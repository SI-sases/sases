# core/services/fs_policy.py
# -*- coding: utf-8 -*-
"""P1：先读后写 / 版本校验（对齐 DSH fs-observation-policy）。"""
import hashlib
import os
from datetime import datetime

from ..db import db_cursor

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if not REPO_ROOT or not os.path.isdir(REPO_ROOT):
    REPO_ROOT = os.getcwd()


def _rel(path: str) -> str:
    p = str(path or "").replace("\\", "/").strip()
    if p.lower().startswith(REPO_ROOT.replace("\\", "/").lower() + "/"):
        p = p[len(REPO_ROOT) + 1:]
    return p.lstrip("/")


def _abs(rel: str) -> str:
    return os.path.join(REPO_ROOT, rel.replace("/", os.sep))


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 64), b""):
            h.update(chunk)
    return h.hexdigest()


def observe(run_id, path: str):
    if not run_id or not path:
        return
    rel = _rel(path)
    ab = _abs(rel)
    try:
        if not os.path.isfile(ab):
            with db_cursor(commit=True) as cur:
                cur.execute("DELETE FROM fs_observations WHERE run_id=? AND path=?", (int(run_id), rel))
            return
        digest = _sha(ab)
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO fs_observations (run_id, path, sha256, observed_at) VALUES (?,?,?,?) "
                "ON CONFLICT(run_id, path) DO UPDATE SET sha256=excluded.sha256, observed_at=excluded.observed_at",
                (int(run_id), rel, digest, datetime.utcnow().replace(microsecond=0).isoformat()),
            )
    except Exception as e:
        print("[fs_policy] observe 失败: " + str(e))


def check_modify(run_id, path: str):
    """返回 (ok, code, message)。未观测→FS_NOT_OBSERVED；版本变了→FS_STALE_VERSION。"""
    if not run_id or not path:
        return True, "", ""
    rel = _rel(path)
    ab = _abs(rel)
    if not os.path.isfile(ab):
        return True, "", ""
    try:
        with db_cursor() as cur:
            cur.execute("SELECT sha256 FROM fs_observations WHERE run_id=? AND path=?", (int(run_id), rel))
            r = cur.fetchone()
        if not r:
            return False, "FS_NOT_OBSERVED", ('[FS_NOT_OBSERVED] cannot modify "' + rel + '": file has not been read; read the file, then retry')
        observed = r["sha256"] if isinstance(r, dict) else r[0]
        if observed != _sha(ab):
            return False, "FS_STALE_VERSION", ('[FS_STALE_VERSION] cannot modify "' + rel + '": file changed since it was read; re-read the file, then retry')
    except Exception as e:
        print("[fs_policy] check 失败: " + str(e))
        return True, "", ""
    return True, "", ""
