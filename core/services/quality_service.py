# core/services/quality_service.py
# 质量保障层：统一除虫机制与挑坏果子机制的污染标记与清理流程
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from ..db import db_cursor
from . import credit_service

# 严重程度定义
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"

# 状态定义
STATUS_PENDING = "pending"
STATUS_CLEANING = "cleaning"
STATUS_CLEANED = "cleaned"
STATUS_ARCHIVED = "archived"

# 来源定义
SOURCE_DEBUG = "debug"
SOURCE_FALSIFY = "falsify"
SOURCE_COMPLIANCE = "compliance"

# 挑坏果子积分规则
FALSIFY_REWARD = 5
FALSIFY_DAILY_LIMIT = 50


def get_today_falsify_points(user_id: int) -> int:
    """获取用户今日已获得的挑坏果子积分总量"""
    today_start = datetime.combine(date.today(), datetime.min.time()).isoformat()
    with db_cursor() as cur:
        cur.execute("""
            SELECT COALESCE(SUM(points), 0) as total FROM contribution_log
            WHERE user_id=? AND event_type='falsify' AND created_at >= ?
        """, (user_id, today_start))
        row = cur.fetchone()
        return row["total"] if row else 0


def create_issue(
    source: str,
    title: str,
    detail: str = "",
    severity: str = SEVERITY_LOW,
    source_id: Optional[str] = None,
    user_id: Optional[int] = None
) -> int:
    """创建一条质量保障记录，返回 issue_id"""
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO quality_issues
            (source, source_id, title, detail, severity, status, user_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            source, source_id, title, detail, severity,
            STATUS_PENDING, user_id, datetime.now().isoformat()
        ))
        return cur.lastrowid


def get_issue(issue_id: int) -> Optional[Dict[str, Any]]:
    """获取单条记录"""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM quality_issues WHERE id=?", (issue_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def list_issues(
    source: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """按条件查询记录"""
    query = "SELECT * FROM quality_issues WHERE 1=1"
    params = []
    if source:
        query += " AND source=?"
        params.append(source)
    if severity:
        query += " AND severity=?"
        params.append(severity)
    if status:
        query += " AND status=?"
        params.append(status)
    if user_id is not None:
        query += " AND user_id=?"
        params.append(user_id)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with db_cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def update_status(issue_id: int, new_status: str) -> bool:
    """更新状态"""
    cleaned_at = datetime.now().isoformat() if new_status == STATUS_CLEANED else None
    with db_cursor(commit=True) as cur:
        if cleaned_at:
            cur.execute(
                "UPDATE quality_issues SET status=?, cleaned_at=? WHERE id=?",
                (new_status, cleaned_at, issue_id)
            )
        else:
            cur.execute(
                "UPDATE quality_issues SET status=? WHERE id=?",
                (new_status, issue_id)
            )
    return True


def submit_falsify_issue(
    user_id: int,
    title: str,
    detail: str,
    source_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    用户提交证伪（挑坏果子）。
    分级规则：
    - 重级：恶意、安全、漏洞相关
    - 中级：错误、异常、崩溃相关
    - 轻级：其他
    同时发放积分（受每日上限限制）
    """
    # 严重程度分级
    severity = SEVERITY_LOW
    detail_lower = detail.lower()
    if any(k in detail_lower for k in ["恶意", "malicious", "安全", "security", "漏洞"]):
        severity = SEVERITY_HIGH
    elif any(k in detail_lower for k in ["错误", "error", "异常", "exception", "崩溃"]):
        severity = SEVERITY_MEDIUM

    issue_id = create_issue(
        source=SOURCE_FALSIFY,
        title=title,
        detail=detail,
        severity=severity,
        source_id=source_id,
        user_id=user_id
    )

    # 积分发放（受每日上限限制）
    today_points = get_today_falsify_points(user_id)
    reward = 0
    if today_points < FALSIFY_DAILY_LIMIT:
        reward = min(FALSIFY_REWARD, FALSIFY_DAILY_LIMIT - today_points)
        try:
            credit_service.add_credit(
                user_id=user_id,
                amount=reward,
                action="挑坏果子",
                detail=f"issue #{issue_id}: {title}",
                event_type="falsify"
            )
        except Exception as e:
            print(f"积分发放失败: {e}")
            reward = 0

    return {
        "issue_id": issue_id,
        "severity": severity,
        "status": STATUS_PENDING,
        "reward": reward,
        "message": "证伪反馈已记录，将进入质量保障流程"
    }


def submit_debug_issue(
    title: str,
    detail: str,
    severity: str = SEVERITY_LOW,
    source_id: Optional[str] = None
) -> int:
    """系统除虫机制提交的污染标记"""
    return create_issue(
        source=SOURCE_DEBUG,
        title=title,
        detail=detail,
        severity=severity,
        source_id=source_id,
        user_id=None
    )


def submit_compliance_issue(
    title: str,
    detail: str,
    severity: str = SEVERITY_MEDIUM,
    source_id: Optional[str] = None
) -> int:
    """合规审查提交的标记"""
    return create_issue(
        source=SOURCE_COMPLIANCE,
        title=title,
        detail=detail,
        severity=severity,
        source_id=source_id,
        user_id=None
    )


def get_rescue_task_pool(limit: int = 20) -> List[Dict[str, Any]]:
    """获取可用于智维空间解救任务的待处理问题"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT * FROM quality_issues
            WHERE status=?
            ORDER BY
                CASE severity
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                    ELSE 4
                END,
                created_at ASC
            LIMIT ?
        """, (STATUS_PENDING, limit))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def get_statistics() -> Dict[str, int]:
    """获取质量保障层统计信息"""
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM quality_issues")
        total = cur.fetchone()["cnt"]

        cur.execute("SELECT COUNT(*) as cnt FROM quality_issues WHERE status=?", (STATUS_PENDING,))
        pending = cur.fetchone()["cnt"]

        cur.execute("SELECT COUNT(*) as cnt FROM quality_issues WHERE status=?", (STATUS_CLEANED,))
        cleaned = cur.fetchone()["cnt"]

        cur.execute("SELECT COUNT(*) as cnt FROM quality_issues WHERE source=?", (SOURCE_FALSIFY,))
        falsify_count = cur.fetchone()["cnt"]

        cur.execute("SELECT COUNT(*) AS cnt FROM quality_issues WHERE source=?", (SOURCE_DEBUG,))
        debug_count = cur.fetchone()["cnt"]

    return {
        "total": total,
        "pending": pending,
        "cleaned": cleaned,
        "falsify": falsify_count,
        "debug": debug_count
    }
