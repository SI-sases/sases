# core/services/compute_service.py
# 官方算力服务：充值、查询、扣费
from datetime import datetime
from typing import Optional, List, Dict, Any
from ..db import db_cursor
from . import credit_service


# 充值套餐（赠送比例）
RECHARGE_PACKAGES = {
    10: 100,      # 10元 = 100算力
    50: 720,      # 50元 = 720算力（+20%）
    100: 2250,    # 100元 = 2250算力（+50%）
}

# 积分兑换算力汇率（5积分 = 1算力）
CREDITS_PER_COMPUTE = 5

# 每日积分兑换上限
DAILY_EXCHANGE_LIMIT = 500


def get_balance(user_id: int) -> int:
    """获取用户算力余额"""
    with db_cursor() as cur:
        cur.execute("SELECT balance FROM user_compute_balance WHERE user_id=?", (user_id,))
        row = cur.fetchone()
    return row["balance"] if row else 0


def get_balance_detail(user_id: int) -> Dict[str, Any]:
    """获取用户算力余额详情"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT balance, total_purchased, total_consumed, updated_at
            FROM user_compute_balance WHERE user_id=?
        """, (user_id,))
        row = cur.fetchone()

    if not row:
        return {
            "balance": 0,
            "total_purchased": 0,
            "total_consumed": 0,
            "updated_at": None
        }
    return dict(row)


def _ensure_balance_row(user_id: int):
    """确保用户算力余额记录存在"""
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT OR IGNORE INTO user_compute_balance (user_id, balance, total_purchased, total_consumed, updated_at)
            VALUES (?, 0, 0, 0, ?)
        """, (user_id, datetime.now().isoformat()))


def add_compute(user_id: int, amount: int, detail: str = "") -> Dict[str, Any]:
    """增加算力（充值或兑换）"""
    if amount <= 0:
        return {"success": False, "message": "数量必须大于 0"}

    _ensure_balance_row(user_id)

    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE user_compute_balance
            SET balance = balance + ?,
                total_purchased = total_purchased + ?,
                updated_at = ?
            WHERE user_id = ?
        """, (amount, amount, datetime.now().isoformat(), user_id))

        cur.execute("SELECT balance FROM user_compute_balance WHERE user_id=?", (user_id,))
        new_balance = cur.fetchone()["balance"]

        cur.execute("""
            INSERT INTO compute_transactions
            (user_id, tx_type, amount, balance_after, detail, created_at)
            VALUES (?, 'recharge', ?, ?, ?, ?)
        """, (user_id, amount, new_balance, detail, datetime.now().isoformat()))

    return {
        "success": True,
        "amount": amount,
        "balance": new_balance
    }


def deduct_compute(user_id: int, amount: int, service_key: str, detail: str = "") -> Dict[str, Any]:
    """扣减算力（消费）"""
    if amount <= 0:
        return {"success": False, "message": "数量必须大于 0"}

    current = get_balance(user_id)
    if current < amount:
        return {"success": False, "message": f"算力不足，需要 {amount}，当前 {current}"}

    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE user_compute_balance
            SET balance = balance - ?,
                total_consumed = total_consumed + ?,
                updated_at = ?
            WHERE user_id = ?
        """, (amount, amount, datetime.now().isoformat(), user_id))

        cur.execute("SELECT balance FROM user_compute_balance WHERE user_id=?", (user_id,))
        new_balance = cur.fetchone()["balance"]

        cur.execute("""
            INSERT INTO compute_transactions
            (user_id, tx_type, amount, balance_after, service_key, detail, created_at)
            VALUES (?, 'consume', ?, ?, ?, ?, ?)
        """, (user_id, -amount, new_balance, service_key, detail, datetime.now().isoformat()))

    return {
        "success": True,
        "amount": amount,
        "balance": new_balance
    }


def list_services() -> List[Dict[str, Any]]:
    """列出所有官方算力服务"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT service_key, service_name, description, unit_cost
            FROM official_compute_services
            WHERE is_active = 1
            ORDER BY unit_cost ASC
        """)
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def get_service(service_key: str) -> Optional[Dict[str, Any]]:
    """获取单个服务详情"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT service_key, service_name, description, unit_cost
            FROM official_compute_services
            WHERE service_key=? AND is_active = 1
        """, (service_key,))
        row = cur.fetchone()
    return dict(row) if row else None


def get_today_exchange_amount(user_id: int) -> int:
    """获取用户今日已通过积分兑换的算力总量"""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    with db_cursor() as cur:
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM compute_transactions
            WHERE user_id=? AND tx_type='exchange' AND created_at >= ?
        """, (user_id, today_start))
        row = cur.fetchone()
    return row["total"] if row else 0


def exchange_credits_for_compute(user_id: int, credits_amount: int) -> Dict[str, Any]:
    """
    用种子积分兑换算力。
    规则：5 积分 = 1 算力，每日上限 500 积分。
    """
    if credits_amount <= 0:
        return {"success": False, "message": "积分数量必须大于 0"}

    if credits_amount % CREDITS_PER_COMPUTE != 0:
        return {"success": False, "message": f"积分必须是 {CREDITS_PER_COMPUTE} 的倍数"}

    # 检查每日上限
    today_exchanged_credits = get_today_exchange_amount(user_id) * CREDITS_PER_COMPUTE
    if today_exchanged_credits + credits_amount > DAILY_EXCHANGE_LIMIT:
        remaining = DAILY_EXCHANGE_LIMIT - today_exchanged_credits
        return {"success": False, "message": f"今日兑换额度不足，剩余 {remaining} 积分"}

    # 检查积分余额
    user_credits = credit_service.get_balance(user_id)
    if user_credits is None:
        return {"success": False, "message": "用户不存在"}
    if user_credits < credits_amount:
        return {"success": False, "message": f"积分不足，需要 {credits_amount}，当前 {user_credits}"}

    # 扣除积分
    credit_service.add_credit(
        user_id=user_id,
        amount=-credits_amount,
        action="积分兑换算力",
        detail=f"消耗 {credits_amount} 积分",
        event_type="exchange"
    )

    # 增加算力
    compute_amount = credits_amount // CREDITS_PER_COMPUTE
    _ensure_balance_row(user_id)

    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE user_compute_balance
            SET balance = balance + ?,
                updated_at = ?
            WHERE user_id = ?
        """, (compute_amount, datetime.now().isoformat(), user_id))

        cur.execute("SELECT balance FROM user_compute_balance WHERE user_id=?", (user_id,))
        new_balance = cur.fetchone()["balance"]

        cur.execute("""
            INSERT INTO compute_transactions
            (user_id, tx_type, amount, balance_after, detail, created_at)
            VALUES (?, 'exchange', ?, ?, ?, ?)
        """, (user_id, compute_amount, new_balance,
              f"消耗 {credits_amount} 积分", datetime.now().isoformat()))

    return {
        "success": True,
        "credits_consumed": credits_amount,
        "compute_gained": compute_amount,
        "compute_balance": new_balance
    }


def get_transactions(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """获取用户算力交易记录"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, tx_type, amount, balance_after, service_key, detail, created_at
            FROM compute_transactions
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT ?
        """, (user_id, limit))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def get_pricing_info() -> Dict[str, Any]:
    """获取算力定价信息（用于前端展示）"""
    return {
        "packages": [
            {"price": 10, "compute": 100, "bonus": "0%"},
            {"price": 50, "compute": 720, "bonus": "+20%"},
            {"price": 100, "compute": 2250, "bonus": "+50%"},
        ],
        "exchange_rate": f"{CREDITS_PER_COMPUTE} 积分 = 1 算力",
        "daily_exchange_limit": DAILY_EXCHANGE_LIMIT
    }
