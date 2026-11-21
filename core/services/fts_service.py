# core/services/fts_service.py
# -*- coding: utf-8 -*-
"""FTS5 trigram 检索：记忆 / 项目库（无 embedding 时的主路径）。"""
import sqlite3

from ..db import db_cursor


def _ensure(cur):
    cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(content, tags, tokenize='trigram')")
    cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS project_fts USING fts5(content, section_path, source_file, tokenize='trigram')")
    for name, table in (("memory_fts", "safety_memory"), ("project_fts", "project_docs")):
        cur.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name=?", (name + "_ai",))
        if cur.fetchone():
            continue
        if table == "safety_memory":
            cur.execute("CREATE TRIGGER memory_fts_ai AFTER INSERT ON safety_memory BEGIN "
                        "INSERT INTO memory_fts(rowid, content, tags) VALUES (new.id, new.content, COALESCE(new.tags,'')); END")
            cur.execute("CREATE TRIGGER memory_fts_ad AFTER DELETE ON safety_memory BEGIN "
                        "DELETE FROM memory_fts WHERE rowid=old.id; END")
            cur.execute("CREATE TRIGGER memory_fts_au AFTER UPDATE ON safety_memory BEGIN "
                        "DELETE FROM memory_fts WHERE rowid=old.id; "
                        "INSERT INTO memory_fts(rowid, content, tags) VALUES (new.id, new.content, COALESCE(new.tags,'')); END")
        else:
            cur.execute("CREATE TRIGGER project_fts_ai AFTER INSERT ON project_docs BEGIN "
                        "INSERT INTO project_fts(rowid, content, section_path, source_file) "
                        "VALUES (new.id, new.content, COALESCE(new.section_path,''), COALESCE(new.source_file,'')); END")
            cur.execute("CREATE TRIGGER project_fts_ad AFTER DELETE ON project_docs BEGIN "
                        "DELETE FROM project_fts WHERE rowid=old.id; END")
            cur.execute("CREATE TRIGGER project_fts_au AFTER UPDATE ON project_docs BEGIN "
                        "DELETE FROM project_fts WHERE rowid=old.id; "
                        "INSERT INTO project_fts(rowid, content, section_path, source_file) "
                        "VALUES (new.id, new.content, COALESCE(new.section_path,''), COALESCE(new.source_file,'')); END")


def ensure():
    with db_cursor(commit=True) as cur:
        _ensure(cur)
        try:
            cur.execute("INSERT INTO memory_fts(rowid, content, tags) "
                        "SELECT id, content, COALESCE(tags,'') FROM safety_memory "
                        "WHERE id NOT IN (SELECT rowid FROM memory_fts)")
        except Exception:
            pass
        try:
            cur.execute("INSERT INTO project_fts(rowid, content, section_path, source_file) "
                        "SELECT id, content, COALESCE(section_path,''), COALESCE(source_file,'') FROM project_docs "
                        "WHERE id NOT IN (SELECT rowid FROM project_fts)")
        except Exception:
            pass


def _q(text):
    """FTS5 trigram 查询：英文词 + 中文 3-gram，OR 组合。"""
    import re
    s = str(text or "").strip()
    if not s:
        return ""
    terms = []
    for w in re.findall(r"[A-Za-z0-9_]{3,}", s):
        terms.append(w)
    for run in re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]{3,}", s):
        for i in range(len(run) - 2):
            terms.append(run[i:i + 3])
    seen = []
    for t in terms:
        if t not in seen:
            seen.append(t)
    if not seen:
        return ""
    return " OR ".join('"' + t.replace('"', '') + '"' for t in seen[:12])


def search_memory(user_id, query, top_k=3, memory_type=None):
    q = _q(query)
    if not q:
        return []
    try:
        ensure()
        sql = ("SELECT m.id, m.memory_type, m.content, m.tags, m.importance, bm25(memory_fts) AS score "
               "FROM memory_fts JOIN safety_memory m ON m.id=memory_fts.rowid "
               "WHERE memory_fts MATCH ? AND m.user_id=?")
        args = [q, int(user_id)]
        if memory_type:
            sql += " AND m.memory_type=?"
            args.append(memory_type)
        sql += " ORDER BY score LIMIT ?"
        args.append(int(top_k))
        with db_cursor() as cur:
            cur.execute(sql, tuple(args))
            rows = [dict(r) for r in cur.fetchall()]
        try:
            from . import keyword_search
            ts = keyword_search.terms(query)
            need = min(2, len(ts)) if ts else 0
            if need:
                rows = [r for r in rows
                        if sum(1 for t in ts if t in (str(r.get("content") or "") + " " + str(r.get("tags") or "")).lower()) >= need]
        except Exception:
            pass
        for r in rows:
            r["_similarity"] = round(min(1.0, 1.0 / (1.0 + abs(float(r.get("score") or 0)))), 4)
        return rows
    except Exception as e:
        print("[fts] memory search 失败: " + str(e))
        return []


def search_project(query, user_id=0, top_k=3):
    q = _q(query)
    if not q:
        return []
    try:
        ensure()
        with db_cursor() as cur:
            cur.execute(
                "SELECT p.id, p.source_file, p.section_path, p.content, p.freshness_score, "
                "bm25(project_fts) AS score FROM project_fts "
                "JOIN project_docs p ON p.id=project_fts.rowid "
                "WHERE project_fts MATCH ? AND p.status='active' "
                "AND (p.user_id=0 OR p.user_id IS NULL OR p.user_id=?) "
                "ORDER BY score LIMIT ?",
                (q, int(user_id or 0), int(top_k)),
            )
            rows = [dict(r) for r in cur.fetchall()]
        try:
            from . import keyword_search
            ts = keyword_search.terms(query)
            need = min(2, len(ts)) if ts else 0
            if need:
                rows = [r for r in rows
                        if sum(1 for t in ts if t in (str(r.get("content") or "") + " " + str(r.get("section_path") or "") + " " + str(r.get("source_file") or "")).lower()) >= need]
        except Exception:
            pass
        for r in rows:
            r["similarity"] = round(min(1.0, 1.0 / (1.0 + abs(float(r.get("score") or 0)))), 4)
            r["score"] = r["similarity"]
        return rows
    except Exception as e:
        print("[fts] project search 失败: " + str(e))
        return []
