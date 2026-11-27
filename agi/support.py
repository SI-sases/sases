"""Support knowledge base, classification, tickets, and escalation."""
from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path

KB_DIR = Path(__file__).resolve().parent / "support_kb"

HUMAN_KEYWORDS = ("退款", "发票", "律师", "法律", "删号", "密码", "泄露", "投诉", "赔偿", "合同")
CATEGORY_WORDS = {
    "billing": ("退款", "发票", "价格", "付款", "钱", "合同"),
    "privacy": ("隐私", "数据", "删号", "泄露", "cookie", "密码"),
    "install": ("安装", "启动", "解压", "双击", "打不开", "闪退"),
    "model": ("key", "模型", "api", "401", "402", "余额", "deepseek"),
    "port": ("端口", "8001", "8029", "占用", "访问"),
    "login": ("登录", "账号", "验证码", "小红书", "抖音", "reddit", "b站", "youtube"),
    "publish": ("发布", "发帖", "提交", "审核", "删除"),
}


def classify(text: str) -> dict:
    low = (text or "").lower()
    category = "other"
    for name, words in CATEGORY_WORDS.items():
        if any(w.lower() in low for w in words):
            category = name
            break
    human = any(w in low for w in HUMAN_KEYWORDS)
    level = "L3" if human else ("L2" if category in {"install", "port", "login", "publish"} else "L1")
    return {"category": category, "level": level, "human_required": human}


def _tokens(text: str) -> list[str]:
    low = (text or "").lower()
    words = re.findall(r"[a-z0-9_]+", low)
    zh = re.findall(r"[\u4e00-\u9fff]", low)
    words += ["".join(zh[i:i + 2]) for i in range(max(0, len(zh) - 1))]
    return [w for w in words if len(w) >= 2]


def search(query: str, limit: int = 3) -> list[dict]:
    tokens = _tokens(query)
    if not tokens:
        return []
    hits = []
    for path in sorted(KB_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        low = text.lower()
        score = sum(low.count(t) for t in tokens)
        if score:
            hits.append({"source": path.name, "score": score, "text": text[:1200]})
    hits.sort(key=lambda x: x["score"], reverse=True)
    return hits[:limit]


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer TEXT,
            source TEXT,
            platform TEXT,
            need TEXT NOT NULL,
            category TEXT NOT NULL,
            level TEXT NOT NULL,
            owner TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            evidence TEXT,
            created_at INTEGER NOT NULL,
            sla_due INTEGER NOT NULL,
            resolved_at INTEGER
        )
        """
    )
    conn.commit()


def create_ticket(conn: sqlite3.Connection, need: str, customer: str = "", source: str = "chat",
                  platform: str = "", evidence: str = "") -> dict:
    info = classify(need)
    ensure_schema(conn)
    now = int(time.time())
    hours = {"L1": 4, "L2": 8, "L3": 24}[info["level"]]
    owner = "human" if info["human_required"] else ("main" if info["level"] == "L1" else "local")
    cur = conn.execute(
        "INSERT INTO support_tickets(customer,source,platform,need,category,level,owner,status,evidence,"
        "created_at,sla_due) VALUES(?,?,?,?,?,?,?, 'open', ?,?,?)",
        (customer, source, platform, need, info["category"], info["level"], owner, evidence, now, now + hours * 3600),
    )
    conn.commit()
    return {"id": int(cur.lastrowid), **info, "owner": owner, "sla_hours": hours}


def list_open(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT id,customer,source,platform,need,category,level,owner,status,created_at,sla_due "
        "FROM support_tickets WHERE status='open' ORDER BY id DESC LIMIT ?",
        (max(1, min(limit, 200)),),
    ).fetchall()
    keys = ("id", "customer", "source", "platform", "need", "category", "level", "owner",
            "status", "created_at", "sla_due")
    return [dict(zip(keys, row)) for row in rows]


def resolve(conn: sqlite3.Connection, ticket_id: int) -> bool:
    ensure_schema(conn)
    cur = conn.execute(
        "UPDATE support_tickets SET status='resolved',resolved_at=? WHERE id=? AND status='open'",
        (int(time.time()), ticket_id),
    )
    conn.commit()
    return cur.rowcount > 0


def draft_reply(query: str) -> dict:
    info = classify(query)
    hits = search(query)
    if info["human_required"]:
        return {"answer": "", "needs_human": True, "reason": "money/legal/security",
                "sources": []}
    if not hits:
        return {"answer": "", "needs_human": False, "reason": "no knowledge base match", "sources": []}
    return {
        "answer": "根据 SASES 知识库，请先参考：" + "、".join(h["source"] for h in hits),
        "needs_human": False,
        "reason": "knowledge base match",
        "sources": [h["source"] for h in hits],
    }
