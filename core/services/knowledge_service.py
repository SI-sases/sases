# core/services/knowledge_service.py
# 知识库服务：本地 BGE + DashScope API 混合模式
import os
import re
import numpy as np
import openai
from datetime import datetime
from typing import Optional, List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from ..db import db_cursor
from .. import config
from .local_embedding import LocalEmbedding


# ========== 阈值配置（按方法区分） ==========
# DashScope API 阈值（实测最优）
API_DUPLICATE_THRESHOLD = 0.68
API_IMPROVEMENT_THRESHOLD = 0.55
API_REUSE_THRESHOLD = 0.65

# 本地 BGE 阈值（分辨力弱，只能判明显相似）
LOCAL_DUPLICATE_THRESHOLD = 0.82
LOCAL_IMPROVEMENT_THRESHOLD = 0.65
LOCAL_REUSE_THRESHOLD = 0.78

# TF-IDF 兜底阈值
TFIDF_DUPLICATE_THRESHOLD = 0.75
TFIDF_IMPROVEMENT_THRESHOLD = 0.45
TFIDF_REUSE_THRESHOLD = 0.60

# 混合模式的边界
HYBRID_LOW = getattr(config, "HYBRID_LOW_THRESHOLD", 0.5)
HYBRID_HIGH = getattr(config, "HYBRID_HIGH_THRESHOLD", 0.85)

# ========== 本地模型 ==========
try:
    local_embedder = LocalEmbedding(model_dir="./bge-small-zh-onnx")
    print("[本地Embedding] 模型加载成功")
except Exception as e:
    print(f"[本地Embedding] 模型加载失败: {e}")
    local_embedder = None

# ========== DashScope 客户端 ==========
_dashscope_client = None
_dashscope_available = False

if config.DASHSCOPE_API_KEY:
    try:
        _dashscope_client = openai.OpenAI(
            api_key=config.DASHSCOPE_API_KEY,
            base_url=config.DASHSCOPE_BASE_URL,
            timeout=30
        )
        _dashscope_available = True
        print("[DashScope] 客户端初始化成功")
    except Exception as e:
        print(f"[DashScope] 初始化失败: {e}")
else:
    print("[DashScope] 未配置 API Key，将只使用本地模型")


def _api_embed(text: str) -> Optional[List[float]]:
    """调用 DashScope API 获取向量"""
    if not _dashscope_available or not text:
        return None
    try:
        resp = _dashscope_client.embeddings.create(
            model=config.DASHSCOPE_EMBEDDING_MODEL,
            input=text.strip()
        )
        return resp.data[0].embedding
    except Exception as e:
        print(f"[DashScope] API 调用失败: {e}")
        return None


def _api_embed_batch(texts: List[str]) -> Optional[List[List[float]]]:
    """批量调用 DashScope API"""
    if not _dashscope_available or not texts:
        return None
    try:
        resp = _dashscope_client.embeddings.create(
            model=config.DASHSCOPE_EMBEDDING_MODEL,
            input=[t.strip() for t in texts]
        )
        return [item.embedding for item in resp.data]
    except Exception as e:
        print(f"[DashScope] 批量调用失败: {e}")
        return None


def _cosine_sim(a, b) -> float:
    va = np.array(a)
    vb = np.array(b)
    if np.linalg.norm(va) == 0 or np.linalg.norm(vb) == 0:
        return 0.0
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))


def _get_thresholds_for_method(method: str) -> Dict[str, float]:
    """根据方法返回对应的阈值"""
    if method in ("api", "hybrid_api"):
        return {
            "duplicate": API_DUPLICATE_THRESHOLD,
            "improvement": API_IMPROVEMENT_THRESHOLD,
            "reuse": API_REUSE_THRESHOLD
        }
    elif method in ("local", "hybrid_local", "hybrid_local_fallback"):
        return {
            "duplicate": LOCAL_DUPLICATE_THRESHOLD,
            "improvement": LOCAL_IMPROVEMENT_THRESHOLD,
            "reuse": LOCAL_REUSE_THRESHOLD
        }
    else:
        return {
            "duplicate": TFIDF_DUPLICATE_THRESHOLD,
            "improvement": TFIDF_IMPROVEMENT_THRESHOLD,
            "reuse": TFIDF_REUSE_THRESHOLD
        }


# ========== TF-IDF 兜底 ==========
def _tokenize(text: str) -> str:
    return " ".join(re.findall(r'[\w\u4e00-\u9fff]+', text.lower()))


def _tfidf_similarity(target: str, candidates: List[str]) -> List[float]:
    if not candidates:
        return []
    try:
        vectorizer = TfidfVectorizer(tokenizer=_tokenize, token_pattern=None)
        all_texts = candidates + [target]
        vectors = vectorizer.fit_transform(all_texts)
        sims = cosine_similarity(vectors[-1], vectors[:-1]).flatten()
        return [float(s) for s in sims]
    except Exception as e:
        print(f"[TF-IDF] 计算失败: {e}")
        return [0.0] * len(candidates)


# ========== 核心：混合相似度计算 ==========
def _compute_similarities(
    query: str,
    candidates: List[str]
) -> Dict[str, Any]:
    """
    混合计算相似度。
    返回：{"sims": [...], "method": str, "used_api": bool}
    """
    mode = getattr(config, "EMBEDDING_MODE", "hybrid")

    # ---------- 纯 API ----------
    if mode == "api" and _dashscope_available:
        query_emb = _api_embed(query)
        if query_emb:
            cand_embs = _api_embed_batch(candidates)
            if cand_embs:
                sims = [_cosine_sim(query_emb, e) for e in cand_embs]
                return {"sims": sims, "method": "api", "used_api": True}

    # ---------- 纯本地 ----------
    if mode == "local" and local_embedder:
        try:
            query_emb = local_embedder.get_embedding(query)[0].tolist()
            sims = []
            for c in candidates:
                cand_emb = local_embedder.get_embedding(c)[0].tolist()
                sims.append(_cosine_sim(query_emb, cand_emb))
            return {"sims": sims, "method": "local", "used_api": False}
        except Exception as e:
            print(f"[本地Embedding] 推理失败: {e}")

    # ---------- 混合 ----------
    if mode == "hybrid" and local_embedder:
        try:
            query_emb = local_embedder.get_embedding(query)[0].tolist()
            local_sims = []
            for c in candidates:
                cand_emb = local_embedder.get_embedding(c)[0].tolist()
                local_sims.append(_cosine_sim(query_emb, cand_emb))

            local_sims_array = np.array(local_sims)
            max_sim = float(local_sims_array.max())

            # 本地足够自信，不调 API
            if max_sim < HYBRID_LOW or max_sim > HYBRID_HIGH:
                return {
                    "sims": local_sims,
                    "method": "hybrid_local",
                    "used_api": False
                }

            # 边界情况：调 API 精确判断
            if _dashscope_available:
                top_indices = local_sims_array.argsort()[-5:][::-1]
                top_candidates = [candidates[i] for i in top_indices]

                api_query_emb = _api_embed(query)
                api_cand_embs = _api_embed_batch(top_candidates)

                if api_query_emb and api_cand_embs:
                    api_sims_top = [
                        _cosine_sim(api_query_emb, e) for e in api_cand_embs
                    ]
                    final_sims = local_sims.copy()
                    for i, idx in enumerate(top_indices):
                        final_sims[idx] = api_sims_top[i]

                    return {
                        "sims": final_sims,
                        "method": "hybrid_api",
                        "used_api": True
                    }

            # API 不可用，用本地结果兜底
            return {
                "sims": local_sims,
                "method": "hybrid_local_fallback",
                "used_api": False
            }

        except Exception as e:
            print(f"[混合模式] 本地推理失败: {e}")

    # ---------- TF-IDF 兜底 ----------
    sims = _tfidf_similarity(query, candidates)
    return {"sims": sims, "method": "tfidf", "used_api": False}


# ========== 核心检索 ==========
def find_similar_solution(
    task_description: str,
    threshold: float = None,
    top_k: int = 3
) -> Optional[Dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, task, solution, verified, source_task_id, contributor_id,
                   hit_count, quality_score, created_at
            FROM knowledge_base
            WHERE verified = 1
            ORDER BY hit_count DESC, quality_score DESC
            LIMIT 500
        """)
        rows = cur.fetchall()

    if not rows:
        return None

    entries = [dict(row) for row in rows]
    tasks = [e["task"] for e in entries]

    result = _compute_similarities(task_description, tasks)
    sims = result["sims"]
    method = result["method"]

    thresholds = _get_thresholds_for_method(method)
    if threshold is None:
        threshold = thresholds["reuse"]

    sims_array = np.array(sims)
    top_indices = sims_array.argsort()[-top_k:][::-1]

    for idx in top_indices:
        similarity = float(sims[idx])
        if similarity >= threshold:
            entry = entries[idx]
            entry["similarity"] = similarity
            entry["method"] = method
            entry["used_api"] = result["used_api"]
            return entry
        else:
            break
    return None


def check_duplicate(text: str) -> Dict[str, Any]:
    with db_cursor() as cur:
        cur.execute("SELECT id, task, solution FROM knowledge_base WHERE verified = 1 LIMIT 500")
        rows = cur.fetchall()

    if not rows:
        return _empty_dup_result()

    entries = [dict(row) for row in rows]
    solutions = [e["solution"] for e in entries]

    result = _compute_similarities(text, solutions)
    sims = result["sims"]
    method = result["method"]

    thresholds = _get_thresholds_for_method(method)
    dup_th = thresholds["duplicate"]
    imp_th = thresholds["improvement"]

    max_idx = int(np.argmax(sims))
    max_sim = float(sims[max_idx])

    if max_sim >= dup_th:
        return {
            "is_duplicate": True,
            "is_improvement": False,
            "is_new": False,
            "similarity": max_sim,
            "matched_id": entries[max_idx]["id"],
            "method": method,
            "used_api": result["used_api"]
        }
    elif max_sim >= imp_th:
        return {
            "is_duplicate": False,
            "is_improvement": True,
            "is_new": False,
            "similarity": max_sim,
            "matched_id": entries[max_idx]["id"],
            "method": method,
            "used_api": result["used_api"]
        }
    else:
        return {
            "is_duplicate": False,
            "is_improvement": False,
            "is_new": True,
            "similarity": max_sim,
            "matched_id": None,
            "method": method,
            "used_api": result["used_api"]
        }


def _empty_dup_result() -> Dict[str, Any]:
    return {
        "is_duplicate": False,
        "is_improvement": False,
        "is_new": True,
        "similarity": 0.0,
        "matched_id": None,
        "method": "none",
        "used_api": False
    }


# ========== 写入与统计 ==========
def add_to_knowledge_base(
    task: str,
    solution: str,
    contributor_id: Optional[int] = None,
    source_task_id: Optional[int] = None,
    quality_score: int = 60,
    branch_a: str = "",
    branch_b: str = ""
) -> Optional[int]:
    dup = check_duplicate(solution)
    if dup["is_duplicate"]:
        print(f"[知识库] 方案重复（相似度 {dup['similarity']:.2f}，方法 {dup['method']}），不写入")
        return None

    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO knowledge_base
            (task, branch_a, branch_b, solution, verified,
             source_task_id, contributor_id, quality_score, created_at)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
        """, (
            task, branch_a, branch_b, solution,
            source_task_id, contributor_id, quality_score,
            datetime.now().isoformat()
        ))
        return cur.lastrowid


def increment_hit_count(kb_id: int, reuser_id: int = None) -> bool:
    """增加命中次数；若传入 reuser_id，触发被动授粉（给原贡献者 +1，日上限 10）"""
    try:
        with db_cursor(commit=True) as cur:
            cur.execute("""
                UPDATE knowledge_base
                SET hit_count = hit_count + 1, last_used_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), kb_id))
            # v0.20: 被动授粉
            if reuser_id:
                cur.execute("SELECT contributor_id FROM knowledge_base WHERE id=?", (kb_id,))
                _row = cur.fetchone()
                _contributor = _row["contributor_id"] if _row else None
                if _contributor and _contributor != reuser_id:
                    try:
                        from . import credit_service as _cs
                        _today = _cs.get_today_passive_points(_contributor)
                        if _today < 10:
                            _cs.add_credit(
                                _contributor, 1,
                                action='被动授粉',
                                detail=f'方案 id={kb_id} 被用户 {reuser_id} 复用',
                                event_type='passive_pollination'
                            )
                            print(f'[知识库] 被动授粉: contributor={_contributor} +1 (今日已得 {_today+1}/10)')
                    except Exception as _pe:
                        print(f'[知识库] 被动授粉失败: {_pe}')
        return True
    except Exception as e:
        print(f"[知识库] 增加命中次数失败: {e}")
        return False


def get_knowledge_entry(kb_id: int) -> Optional[Dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM knowledge_base WHERE id=?", (kb_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def get_contributor_stats(user_id: int) -> Dict[str, Any]:
    with db_cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) as total_entries,
                   COALESCE(SUM(hit_count), 0) as total_hits
            FROM knowledge_base
            WHERE contributor_id = ?
        """, (user_id,))
        row = cur.fetchone()
    return {
        "total_entries": row["total_entries"] if row else 0,
        "total_hits": row["total_hits"] if row else 0
    }


def list_recent_entries(limit: int = 20) -> List[Dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, task, solution, contributor_id, hit_count, quality_score, created_at
            FROM knowledge_base
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]
