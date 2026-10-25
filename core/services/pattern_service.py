# core/services/pattern_service.py
"""经验库核心服务 - P0 只写不读阶段"""
import hashlib
import re
import numpy as np
from typing import Optional
from datetime import datetime, timedelta
from ..db import db_cursor
from .local_embedding import LocalEmbedding

_embedder = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = LocalEmbedding()
    return _embedder


DEDUP_SIMILARITY_THRESHOLD = 0.85
RECALL_SIMILARITY_THRESHOLD = 0.60
MAX_CANDIDATES = 200
CONFIDENCE_INIT = 0.5

# 正则里不含引号字符，避免 JSON 传输时的转义问题
SANITIZE_RULES = [
    (re.compile(r"[A-Za-z]:[\\/][^\s<>|]+"), "<PATH>"),
    (re.compile(r"/(?:Users|home|var|etc|usr|opt)/[^\s<>|]+"), "<PATH>"),
    (re.compile(r"sases_[a-zA-Z0-9]+"), "<SASES_ID>"),
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "<API_KEY>"),
    (re.compile(r"\b(?:10|172|192)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "<PRIVATE_IP>"),
]


def sanitize(text):
    if not text:
        return text
    for pattern, replacement in SANITIZE_RULES:
        text = pattern.sub(replacement, text)
    return text


def _compute_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _embed_to_blob(emb):
    return np.asarray(emb, dtype=np.float32).flatten().tobytes()


def _blob_to_embed(blob):
    if not blob:
        return None
    try:
        return np.frombuffer(blob, dtype=np.float32)
    except Exception:
        return None


def _cosine_sim(a, b):
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


def _build_context_signature(role, action, file_type=None, task_kind=None):
    """构建领域上下文签名"""
    role = (role or "unknown").lower()
    action = (action or "unknown").lower()
    if task_kind:
        return f"{role}:{action}:{task_kind}"
    if file_type:
        return f"{role}:{action}:{file_type}"
    return f"{role}:{action}"


def _classify_pattern_type(status, review_result, step_count):
    """判断 pattern 类型"""
    if status == "blocked":
        return "blocked"
    if status == "format_error":
        return "format"
    if review_result == "retry":
        return "failure"
    if step_count > 1:
        return "sequence"
    return "success"


def _extract_pattern_key(step, status, review_result):
    # 从单个步骤生成 pattern_key（细分版）
    cmd = (step.get("command") or step.get("module_id") or "unknown").strip()
    if not cmd:
        return "unknown"
    if step.get("type") == "harness":
        base = f"harness_{step.get('module_id', 'unknown')}"
    else:
        first_word = cmd.split()[0].lower() if cmd.split() else "unknown"
        base = f"cmd_{first_word}"
    reason_text = ""
    for key in ("reason", "output", "error", "review_reason", "detail"):
        v = step.get(key)
        if v:
            reason_text += " " + str(v)
    reason_lower = reason_text.lower()
    if status == "blocked":
        if "白名单" in reason_lower or "whitelist" in reason_lower:
            return f"{base}_blocked_whitelist"
        if "受保护" in reason_lower or "protected" in reason_lower:
            return f"{base}_blocked_protected"
        if "禁止字符" in reason_lower or "dangerous" in reason_lower:
            return f"{base}_blocked_dangerous_char"
        if "权限" in reason_lower or "permission" in reason_lower:
            return f"{base}_blocked_permission"
        return f"{base}_blocked"
    if status == "format_error":
        return f"{base}_format_error"
    if review_result == "retry":
        if "未找到" in reason_lower or "not found" in reason_lower:
            return f"{base}_retry_not_found"
        if "出现" in reason_lower and "次" in reason_lower:
            return f"{base}_retry_ambiguous"
        if "缺少" in reason_lower or "missing" in reason_lower:
            return f"{base}_retry_missing_param"
        if "不存在" in reason_lower:
            return f"{base}_retry_not_exist"
        return f"{base}_retry"
    return f"{base}_ok"


def _upsert_pattern(domain, pattern_key, pattern_type, context_signature, role, evidence, source_task_id, user_id):
    """写入或更新一条 pattern"""
    now = datetime.now().isoformat()

    with db_cursor() as cur:
        cur.execute(
            "SELECT id, hit_count, success_count, fail_count, last_success_at FROM interaction_patterns "
            "WHERE domain=? AND pattern_key=? AND context_signature=?",
            (domain, pattern_key, context_signature)
        )
        row = cur.fetchone()

    if row:
        new_hit = (row["hit_count"] or 0) + 1
        if pattern_type == "success":
            new_success = (row["success_count"] or 0) + 1
            new_fail = row["fail_count"] or 0
            new_last_success = now
        else:
            new_success = row["success_count"] or 0
            new_fail = (row["fail_count"] or 0) + 1
            new_last_success = row["last_success_at"]
        new_conf = (new_success + 1) / (new_success + new_fail + 2)
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE interaction_patterns SET hit_count=?, success_count=?, fail_count=?, "
                "confidence=?, last_hit_at=?, last_success_at=?, updated_at=? WHERE id=?",
                (new_hit, new_success, new_fail, new_conf, now, new_last_success, now, row["id"])
            )
        return row["id"]

    if pattern_type == "success":
        init_success, init_fail = 1, 0
    else:
        init_success, init_fail = 0, 1
    init_conf = (init_success + 1) / (init_success + init_fail + 2)

    try:
        emb = _get_embedder().get_embedding(evidence)
        with db_cursor() as cur:
            cur.execute(
                "SELECT id, pattern_key, evidence FROM interaction_patterns WHERE domain=? AND role=? AND evidence IS NOT NULL LIMIT ?",
                (domain, role, MAX_CANDIDATES)
            )
            candidates = cur.fetchall()
        query_vec = np.asarray(emb, dtype=np.float32).flatten()
        for c in candidates:
            c_key = c["pattern_key"] if "pattern_key" in c.keys() else ""
            if c_key and c_key != pattern_key:
                continue
            c_emb = _get_embedder().get_embedding(c["evidence"])
            if _cosine_sim(query_vec, np.asarray(c_emb, dtype=np.float32).flatten()) >= DEDUP_SIMILARITY_THRESHOLD:
                with db_cursor(commit=True) as cur2:
                    cur2.execute(
                        "UPDATE interaction_patterns SET hit_count=hit_count+1, "
                        "success_count=success_count+?, fail_count=fail_count+?, "
                        "confidence=(success_count+1.0)/(success_count+fail_count+2.0), "
                        "last_hit_at=?, updated_at=? WHERE id=?",
                        (1 if pattern_type == "success" else 0,
                         0 if pattern_type == "success" else 1,
                         now, now, c["id"])
                    )
                return c["id"]
    except Exception as e:
        print(f"[pattern] 语义去重失败: {e}")

    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO interaction_patterns "
            "(domain, pattern_key, pattern_type, context_signature, role, evidence, "
            "confidence, hit_count, success_count, fail_count, distinct_user_count, "
            "last_hit_at, last_success_at, status, source_task_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 1, ?, ?, 'tentative', ?, ?, ?)",
            (domain, pattern_key, pattern_type, context_signature, role, evidence,
             init_conf, init_success, init_fail, now,
             now if pattern_type == "success" else None,
             source_task_id, now, now)
        )
        return cur.lastrowid


def record_pattern(user_id, task_id, domain, results):
    """任务完成后，从 results 中提取 pattern 并入库"""
    if not results:
        return 0
    count = 0
    for step in results:
        try:
            status = step.get("status", "unknown")
            review = step.get("review", "?")
            pattern_key = _extract_pattern_key(step, status, review)
            pattern_type = _classify_pattern_type(status, review, len(results))
            file_type = None
            cmd = step.get("command") or ""
            if cmd and "." in cmd:
                for p in cmd.split():
                    if "." in p and len(p) < 30:
                        file_type = p.split(".")[-1].lower()
                        break
            context_sig = _build_context_signature(
                role=step.get("role", "executor"),
                action=step.get("type", "command"),
                file_type=file_type
            )
            evidence_raw = f"{pattern_key} | {step.get('description', '')} | {step.get('reason', '')}"
            evidence = sanitize(evidence_raw)[:500]
            _upsert_pattern(domain, pattern_key, pattern_type, context_sig, "executor", evidence, task_id, user_id)
            count += 1
        except Exception as e:
            print(f"[pattern] 提取失败: {e}")
    return count


def finalize_patterns(hours=24):
    """将 N 小时前的 tentative pattern 转为 active"""
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    now = datetime.now().isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE interaction_patterns SET status='active', updated_at=? "
            "WHERE status='tentative' AND created_at < ?",
            (now, cutoff)
        )
        activated = cur.rowcount
    if activated:
        print(f"[pattern] {activated} 条 tentative 转为 active")
    _refresh_domain_counts()
    return activated


def _refresh_domain_counts():
    """更新 domains 表的 pattern 计数"""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "SELECT domain, COUNT(*) as cnt FROM interaction_patterns WHERE status='active' GROUP BY domain"
        )
        rows = cur.fetchall()
        counts = {r["domain"]: r["cnt"] for r in rows}
        cur.execute("SELECT domain FROM domains")
        all_domains = [r["domain"] for r in cur.fetchall()]
        for d in all_domains:
            cur.execute(
                "UPDATE domains SET pattern_count=? WHERE domain=?",
                (counts.get(d, 0), d)
            )


def retrieve_patterns(user_input, domain='dev', top_k=3, min_confidence=0.5):
    '检索相关 pattern'
    with db_cursor() as cur:
        cur.execute(
            'SELECT id, pattern_key, pattern_type, context_signature, role, evidence, confidence, hit_count, status FROM interaction_patterns WHERE status IN (?, ?) AND confidence >= ? ORDER BY hit_count DESC, confidence DESC LIMIT 50',
            ('active', 'tentative', min_confidence)
        )
        rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        return []

    try:
        query_vec = np.asarray(_get_embedder().get_embedding(user_input), dtype=np.float32).flatten()
    except Exception as e:
        print(f'[pattern] 查询 embedding 失败: {e}')
        return rows[:top_k]

    scored = []
    for r in rows:
        try:
            txt = r.get('evidence') or r.get('pattern_key') or ''
            r_emb = np.asarray(_get_embedder().get_embedding(txt), dtype=np.float32).flatten()
            sim = _cosine_sim(query_vec, r_emb)
            scored.append((sim, r))
        except Exception:
            continue

    if not scored:
        return rows[:top_k]

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for sim, r in scored[:top_k]:
        r['_similarity'] = round(sim, 4)
        results.append(r)
    return results


def format_patterns_for_prompt(patterns, max_chars=100):
    '格式化为可注入 prompt 的文本'
    if not patterns:
        return ''
    lines = ['【历史模式】']
    for p in patterns:
        ptype = p.get('pattern_type') or ''
        ev = (p.get('evidence') or '')[:max_chars]
        conf = p.get('confidence') or 0
        lines.append('- [' + ptype + '] ' + ev + ' (置信度' + str(round(conf, 2)) + ')')
    return chr(10).join(lines)



def get_stats():
    """返回经验库统计"""
    _refresh_domain_counts()
    result = {"total": 0, "domains": [], "status_breakdown": {}}
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM interaction_patterns")
        result["total"] = cur.fetchone()["cnt"]
        cur.execute(
            "SELECT domain, pattern_count, active FROM domains ORDER BY pattern_count DESC"
        )
        result["domains"] = [dict(r) for r in cur.fetchall()]
        cur.execute(
            "SELECT status, COUNT(*) as cnt FROM interaction_patterns GROUP BY status"
        )
        result["status_breakdown"] = {r["status"]: r["cnt"] for r in cur.fetchall()}
        cur.execute(
            "SELECT pattern_key, pattern_type, confidence, hit_count, status FROM interaction_patterns "
            "ORDER BY hit_count DESC LIMIT 10"
        )
        result["top_patterns"] = [dict(r) for r in cur.fetchall()]
    return result
