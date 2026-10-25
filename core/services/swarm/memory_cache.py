from typing import Dict, Any

# ========== 全局内存缓存 ==========
_pending: Dict[str, Dict[str, Any]] = {}
_feedback_table_ready = False
_review_table_ready = False
