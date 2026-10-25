# core/services/market_service.py
from ..db import db_cursor


def create_order(user_id: int, order_type: str, description: str, price: float):
    """发布交易订单，仅允许买算力或卖算力"""
    if order_type not in ("buy_compute", "sell_compute"):
        raise ValueError("订单类型仅支持 buy_compute 或 sell_compute")
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO market_orders (user_id, order_type, description, price, status)
            VALUES (?, ?, ?, ?, 'open')
        """, (user_id, order_type, description, price))
        return cur.lastrowid


def list_orders(limit: int = 50, status: str = None):
    with db_cursor() as cur:
        if status:
            cur.execute("""
                SELECT o.id, o.user_id, u.username as owner_name, o.order_type, o.description,
                       o.price, o.status, o.created_at
                FROM market_orders o
                JOIN users u ON o.user_id = u.id
                WHERE o.status=?
                ORDER BY o.created_at DESC
                LIMIT ?
            """, (status, limit))
        else:
            cur.execute("""
                SELECT o.id, o.user_id, u.username as owner_name, o.order_type, o.description,
                       o.price, o.status, o.created_at
                FROM market_orders o
                JOIN users u ON o.user_id = u.id
                ORDER BY o.created_at DESC
                LIMIT ?
            """, (limit,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def accept_order(user_id: int, order_id: int):
    """接单，完成积分转移"""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM market_orders WHERE id=?", (order_id,))
        order = cur.fetchone()
        if not order:
            raise ValueError("订单不存在")
        if order["status"] != "open":
            raise ValueError("订单已被接取")
        if order["user_id"] == user_id:
            raise ValueError("不能接自己的订单")

        price = order["price"]
        cur.execute("SELECT credits FROM users WHERE id=?", (user_id,))
        acceptor = cur.fetchone()
        if not acceptor or acceptor["credits"] < price:
            raise ValueError("积分不足")

        # 根据订单类型，买方是发布者还是接单者
        # buy_compute：发布者用积分购买算力，接单者提供算力，接单者获得积分
        # sell_compute：发布者出售算力，接单者用积分购买，发布者获得积分
        if order["order_type"] == "buy_compute":
            # 买方是发布者，卖方是接单者
            buyer_id = order["user_id"]
            seller_id = user_id
        elif order["order_type"] == "sell_compute":
            # 卖方是发布者，买方是接单者
            buyer_id = user_id
            seller_id = order["user_id"]
        else:
            raise ValueError("未知订单类型")

        provider_income = price * 0.95
        platform_fee = price * 0.05

        with db_cursor(commit=True) as cur2:
            cur2.execute("UPDATE users SET credits = credits - ? WHERE id=?", (price, buyer_id))
            cur2.execute("UPDATE users SET credits = credits + ? WHERE id=?", (provider_income, seller_id))
            cur2.execute("UPDATE market_orders SET status='completed', accepted_by=? WHERE id=?", (user_id, order_id))
            cur2.execute("""
                INSERT INTO contribution_log (user_id, action, event_type, points, detail)
                VALUES (?, '交易市场支出', 'market', ?, ?)
            """, (buyer_id, -price, f"订单#{order_id}"))
            cur2.execute("""
                INSERT INTO contribution_log (user_id, action, event_type, points, detail)
                VALUES (?, '交易市场收入', 'market', ?, ?)
            """, (seller_id, provider_income, f"订单#{order_id}"))

    return {"status": "completed", "provider_income": provider_income, "platform_fee": platform_fee}
