# core/services/memory_service.py
from typing import Optional, List
import json
import hashlib
import numpy as np
from datetime import datetime, timedelta
from ..db import db_cursor
from .local_embedding import LocalEmbedding

# ========== Embedding 单例 ==========
_embedder = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = LocalEmbedding()
    return _embedder


# ========== 常量 ==========
DEDUP_SIMILARITY_THRESHOLD = 0.95       # 语义去重阈值
RECALL_SIMILARITY_THRESHOLD = 0.55      # 检索最低相似度
MAX_CANDIDATES = 200                    # 单次检索候选上限


# ========== 内部工具 ==========

def _compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _embed_to_blob(emb) -> bytes:
    return np.asarray(emb, dtype=np.float32).flatten().tobytes()


def _blob_to_embed(blob) -> Optional[np.ndarray]:
    if not blob:
        return None
    try:
        return np.frombuffer(blob, dtype=np.float32)
    except Exception:
        return None


def _cosine_sim(a, b) -> float:
    if a is None or b is None:
        return 0.0
    a = np.asarray(a, dtype=np.float32).flatten()
    b = np.asarray(b, dtype=np.float32).flatten()
    if a.shape != b.shape:
        return 0.0
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ========== 核心接口 ==========

def remember(
    user_id: int,
    memory_type: str,
    content: str,
    agent_id: str = None,
    group_id: int = None,
    tags: str = None,
    importance: float = 0.5,
    full_data: dict = None,
    expires_at: str = None,
    task_id: str = None,
    enable_dedup: bool = True
) -> int:
    """写入一条安全记忆（带 hash + 语义双层去重）"""
    full_data_json = json.dumps(full_data, ensure_ascii=False) if full_data else None
    content_hash = _compute_hash(content)

    # 1. Hash 精确去重
    if enable_dedup:
        with db_cursor() as cur:
            cur.execute(
                "SELECT id FROM safety_memory WHERE user_id=? AND content_hash=? LIMIT 1",
                (user_id, content_hash)
            )
            row = cur.fetchone()
            if row:
                with db_cursor(commit=True) as cur2:
                    cur2.execute(
                        "UPDATE safety_memory SET created_at=? WHERE id=?",
                        (datetime.now().isoformat(), row["id"])
                    )
                return row["id"]

    # 2. 生成 embedding
    emb = None
    try:
        emb = _get_embedder().get_embedding(content)
    except Exception as e:
        print(f"[memory] embedding 生成失败: {e}")

    # 3. 语义去重
    if enable_dedup and emb is not None:
        with db_cursor() as cur:
            cur.execute(
                "SELECT id, embedding FROM safety_memory WHERE user_id=? AND memory_type=? AND embedding IS NOT NULL LIMIT ?",
                (user_id, memory_type, MAX_CANDIDATES)
            )
            rows = cur.fetchall()
        query_emb = np.asarray(emb, dtype=np.float32).flatten()
        for row in rows:
            old_emb = _blob_to_embed(row["embedding"])
            sim = _cosine_sim(query_emb, old_emb)
            if sim >= DEDUP_SIMILARITY_THRESHOLD:
                with db_cursor(commit=True) as cur2:
                    cur2.execute(
                        "UPDATE safety_memory SET created_at=? WHERE id=?",
                        (datetime.now().isoformat(), row["id"])
                    )
                print(f"[memory] 语义重复 (sim={sim:.3f})，跳过写入")
                return row["id"]

    # 4. 正常写入
    emb_blob = _embed_to_blob(emb) if emb is not None else None
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO safety_memory
            (memory_type, content, full_data, agent_id, user_id, group_id, importance, tags, expires_at, task_id, embedding, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (memory_type, content, full_data_json, agent_id, user_id, group_id, importance, tags, expires_at, task_id, emb_blob, content_hash))
        return cur.lastrowid


def recall(
    user_id: int,
    query: str,
    top_k: int = 5,
    memory_type: str = None,
    group_id: int = None,
    similarity_threshold: float = RECALL_SIMILARITY_THRESHOLD
) -> List[dict]:
    """语义检索用户的记忆"""
    with db_cursor() as cur:
        sql = "SELECT * FROM safety_memory WHERE user_id=?"
        params = [user_id]
        if memory_type:
            sql += " AND memory_type=?"
            params.append(memory_type)
        if group_id is not None:
            sql += " AND group_id=?"
            params.append(group_id)
        sql += " ORDER BY importance DESC, created_at DESC LIMIT ?"
        params.append(MAX_CANDIDATES)
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        return []

    # 查询 embedding
    try:
        query_emb = np.asarray(_get_embedder().get_embedding(query), dtype=np.float32).flatten()
    except Exception as e:
        print(f"[memory] 查询 embedding 失败，降级关键词: {e}")
        query_lower = query.lower()
        results = []
        for row in rows:
            if query_lower in row["content"].lower() or (row["tags"] and query_lower in row["tags"].lower()):
                row.pop("embedding", None)
                results.append(row)
                if len(results) >= top_k:
                    break
        return results

    # 相似度计算
    scored = []
    for row in rows:
        old_emb = _blob_to_embed(row.get("embedding"))
        if old_emb is None:
            if query.lower() in row["content"].lower():
                scored.append((0.5, row))
            continue
        sim = _cosine_sim(query_emb, old_emb)
        if sim >= similarity_threshold:
            scored.append((sim, row))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for sim, row in scored[:top_k]:
        row_out = {k: v for k, v in row.items() if k != "embedding"}
        row_out["_similarity"] = round(sim, 4)
        results.append(row_out)
    return results


def recall_by_type(
    user_id: int,
    memory_type: str,
    top_k: int = 5,
    group_id: int = None
) -> List[dict]:
    """按类型直接获取最新记忆"""
    with db_cursor() as cur:
        sql = "SELECT * FROM safety_memory WHERE user_id=? AND memory_type=?"
        params = [user_id, memory_type]
        if group_id is not None:
            sql += " AND group_id=?"
            params.append(group_id)
        sql += " ORDER BY created_at DESC, importance DESC LIMIT ?"
        params.append(top_k)
        cur.execute(sql, params)
        rows = cur.fetchall()

    results = []
    for row in rows:
        row_dict = dict(row)
        row_dict.pop("embedding", None)
        results.append(row_dict)
    return results


def forget(user_id: int, memory_id: int) -> bool:
    """删除用户的一条记忆"""
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM safety_memory WHERE id=? AND user_id=?", (memory_id, user_id))
        return cur.rowcount > 0


def backfill_embeddings(batch_size: int = 100) -> int:
    """为现有记忆补生成 embedding（迁移用）"""
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, content FROM safety_memory WHERE embedding IS NULL LIMIT ?",
            (batch_size,)
        )
        rows = cur.fetchall()

    if not rows:
        return 0

    count = 0
    for row in rows:
        try:
            emb = _get_embedder().get_embedding(row["content"])
            blob = _embed_to_blob(emb)
            ch = _compute_hash(row["content"])
            with db_cursor(commit=True) as cur:
                cur.execute(
                    "UPDATE safety_memory SET embedding=?, content_hash=? WHERE id=?",
                    (blob, ch, row["id"])
                )
            count += 1
        except Exception as e:
            print(f"[memory] backfill 失败 id={row['id']}: {e}")
    return count


def summarize_work_logs(user_id: int, hours: int = 24) -> int:
    """总结最近 N 小时的工作日志，并写入记忆库"""
    since = (datetime.now() - timedelta(hours=hours)).isoformat()

    with db_cursor() as cur:
        cur.execute("""
            SELECT command, output, status, duration_ms, created_at
            FROM work_logs
            WHERE user_id=? AND created_at >= ?
            ORDER BY created_at ASC
        """, (user_id, since))
        rows = cur.fetchall()

    if not rows:
        return 0

    total = len(rows)
    success_count = sum(1 for r in rows if r["status"] == "success")
    failed_count = total - success_count
    avg_duration = sum(r["duration_ms"] or 0 for r in rows) / total

    cmd_counts = {}
    for r in rows:
        base_cmd = r["command"].strip().split()[0] if r["command"].strip() else "unknown"
        cmd_counts[base_cmd] = cmd_counts.get(base_cmd, 0) + 1

    common_cmds = sorted(cmd_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    content = (
        f"过去{hours}小时工作日志总结\n"
        f"总任务数: {total}\n"
        f"成功: {success_count}\n"
        f"失败: {failed_count}\n"
        f"平均耗时: {avg_duration:.0f} ms\n"
        f"常用命令: {', '.join([f'{cmd}({cnt})' for cmd, cnt in common_cmds])}"
    )

    return remember(
        user_id=user_id,
        memory_type="periodic_summary",
        content=content,
        tags="work_summary",
        importance=0.7
    )
