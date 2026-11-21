# core/services/agent_question_service.py
# -*- coding: utf-8 -*-
"""ask_user v1：模型提问 → 卡片 → 用户回答。"""
from datetime import datetime

from ..db import db_cursor

MARKER = "[ASK_USER]:"


def parse(content):
    """返回 (展示文本, 问题)；没有标记时问题为 None。"""
    text = str(content or "")
    if MARKER not in text:
        return text, None
    idx = text.index(MARKER)
    question = text[idx + len(MARKER):].strip()
    clean = (text[:idx] + text[idx + len(MARKER):]).strip()
    return clean, question


def create(conversation_id, question, run_id=None):
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO agent_questions (conversation_id, run_id, question, status, created_at) "
            "VALUES (?,?,?,'pending',?)",
            (int(conversation_id), run_id, str(question or "").strip(),
             datetime.now().isoformat()),
        )
        return cur.lastrowid


def answer(question_id, answer_text):
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE agent_questions SET status='answered', answer=?, answered_at=? WHERE id=?",
            (str(answer_text or ""), datetime.now().isoformat(), int(question_id)),
        )
        return cur.rowcount > 0


def get(question_id):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM agent_questions WHERE id=?", (int(question_id),))
        row = cur.fetchone()
        return dict(row) if row else None


def pending(conversation_id):
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, question, created_at FROM agent_questions "
            "WHERE conversation_id=? AND status='pending' ORDER BY id DESC LIMIT 5",
            (int(conversation_id),),
        )
        return [dict(r) for r in cur.fetchall()]
