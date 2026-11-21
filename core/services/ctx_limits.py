# -*- coding: utf-8 -*-
"""SASES 上下文限制集中配置 —— 放宽版（先不考虑成本）"""

# 总预算（内部值，最终受模型物理上限约束）
CTX_BUDGET = 128000

# 模型物理硬上限（保护真实 API 不报 400）
MODEL_HARD_LIMIT = 60000   # DeepSeek 64K - 4K 安全余量
OUTPUT_RESERVE = 8000       # 给输出留的空间

# doc_paste 检测
DOC_PASTE_MIN_CHARS = 500
DOC_PASTE_MAX_CHARS = 200000

# history 加载
HISTORY_MAX_COUNT = 200
HISTORY_RECENT_FULL = 50     # 最近 50 条完全不截断
HISTORY_NEAR_LIMIT = 10000   # 51-100 条
HISTORY_MID_LIMIT = 5000     # 101-150 条
HISTORY_FAR_LIMIT = 2000     # 151-200 条

# enrich_plan_input 兜底
ENRICH_FALLBACK_COUNT = 50
ENRICH_FALLBACK_BUDGET_RATIO = 0.7

# 检索 top_k
TASK_CTX_TOP_K = 10
SUCCESS_RECALL_TOP_K = 10
FAILURE_RECALL_TOP_K = 5
PROJECT_RECALL_TOP_K = 5

# 单条消息 token 上限（防止单条撑爆）
PER_MESSAGE_TOKEN_LIMIT = 50000
