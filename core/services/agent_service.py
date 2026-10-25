# core/services/agent_service.py
from ..db import db_cursor

def list_my_agents(user_id: int):
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, model_type, name, provider, node_url, model_name, capabilities, is_shared, visibility, price
            FROM model_configs
            WHERE user_id=?
            ORDER BY created_at DESC
        """, (user_id,))
        rows = cur.fetchall()

    agents = []
    for row in rows:
        agent_type = "local" if row["model_type"] == "local" else "api"
        capability = row["capabilities"] or ("本地模型" if agent_type == "local" else "云端模型")
        detail = ""
        if agent_type == "local":
            detail = f"{row['model_name']} @ {row['node_url']}"
        else:
            detail = f"{row['provider']}"

        agents.append({
            "agent_id": row["id"],
            "name": row["name"],
            "type": agent_type,
            "capability": capability,
            "detail": detail,
            "is_shared": row["is_shared"],
            "visibility": row["visibility"],
            "price": row["price"]
        })

    # 确保每个用户都有 sases_assistant 虚拟助手
    _has_sases_assistant = any(
        (a.get("agent_id") or "").startswith("sases_assistant") for a in agents
    )
    if not _has_sases_assistant:
        agents.insert(0, {
            "agent_id": f"sases_assistant_{user_id}",
            "name": "SASES 助手",
            "type": "api",
            "capability": "知识库导入 / 项目管理 / 系统对话",
            "detail": "系统内置",
            "is_shared": 0,
            "visibility": "private",
            "price": 0,
            "is_virtual": True
        })

    return agents

def list_friend_agents(user_id: int):
    friends = []
    with db_cursor() as cur:
        # 1. 查询所有 accepted 的好友关系
        cur.execute("""
            SELECT af.friend_agent_id, af.target_user_id, af.friend_mode
            FROM agent_friendships af
            WHERE af.user_id=? AND af.status='accepted'
        """, (user_id,))
        rows = cur.fetchall()
        
        for row in rows:
            target_uid = row["target_user_id"]
            friend_aid = row["friend_agent_id"]
            
            # 如果是真人好友
            if target_uid:
                cur.execute("SELECT username FROM users WHERE id=?", (target_uid,))
                u_row = cur.fetchone()
                name = u_row["username"] if u_row else f"User{target_uid}"
                
                # 查双向会话 ID
                cur.execute("""
                    SELECT id FROM conversations 
                    WHERE (user_id=? AND target_user_id=?) OR (user_id=? AND target_user_id=?) 
                    AND is_friend_chat=1 LIMIT 1
                """, (user_id, target_uid, target_uid, user_id))
                conv_row = cur.fetchone()
                conv_id = conv_row["id"] if conv_row else None
                
                friends.append({
                    "agent_id": f"user_{target_uid}",
                    "name": name,
                    "owner": "用户",
                    "type": "friend",
                    "conversation_id": conv_id,
                    "target_user_id": target_uid,
                    "capability": "真人好友",
                    "detail": "普通用户",
                    "price": 0,
                    "friend_mode": row["friend_mode"]
                })
            # 如果是智能体好友
            elif friend_aid:
                cur.execute("""
                    SELECT mc.name, mc.provider, mc.model_name, mc.capabilities, mc.model_type, mc.price, u.username as owner_name
                    FROM model_configs mc
                    JOIN users u ON mc.user_id = u.id
                    WHERE mc.id=?
                """, (friend_aid,))
                mc_row = cur.fetchone()
                if mc_row:
                    friends.append({
                        "agent_id": friend_aid,
                        "name": mc_row["name"],
                        "owner": mc_row["owner_name"],
                        "type": "friend",
                        "conversation_id": None,
                        "target_user_id": None,
                        "capability": mc_row["capabilities"] or "云端模型",
                        "detail": f"{mc_row['provider'] or mc_row['model_name']}",
                        "price": mc_row["price"],
                        "friend_mode": row["friend_mode"]
                    })
    return friends

def search_agents(user_id: int, q: str, include_self: bool = False):
    pattern = f"%{q}%"
    with db_cursor() as cur:
        if include_self:
            cur.execute("""
                SELECT mc.id, mc.name, mc.provider, mc.model_name, mc.capabilities, mc.model_type, u.username as owner_name, mc.price
                FROM model_configs mc
                JOIN users u ON mc.user_id = u.id
                WHERE (mc.user_id = ? OR (mc.is_shared = 1 OR mc.visibility = 'public'))
                  AND (mc.name LIKE ? OR mc.provider LIKE ? OR mc.model_name LIKE ?)
                LIMIT 20
            """, (user_id, pattern, pattern, pattern))
        else:
            cur.execute("""
                SELECT mc.id, mc.name, mc.provider, mc.model_name, mc.capabilities, mc.model_type, u.username as owner_name, mc.price
                FROM model_configs mc
                JOIN users u ON mc.user_id = u.id
                WHERE mc.user_id != ?
                  AND (mc.is_shared = 1 OR mc.visibility = 'public')
                  AND (mc.name LIKE ? OR mc.provider LIKE ? OR mc.model_name LIKE ?)
                LIMIT 20
            """, (user_id, pattern, pattern, pattern))
        rows = cur.fetchall()

    results = []
    for row in rows:
        results.append({
            "agent_id": row["id"],
            "name": row["name"],
            "owner": row["owner_name"],
            "type": "local" if row["model_type"] == "local" else "api",
            "capability": row["capabilities"] or "云端模型",
            "detail": f"{row['provider'] or row['model_name']}",
            "price": row["price"]
        })
    return results

def send_friend_request(user_id: int, agent_id: str):
    """发送好友请求，记录目标用户（智能体所有者）"""
    with db_cursor() as cur:
        cur.execute("SELECT user_id FROM model_configs WHERE id=?", (agent_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError("智能体不存在")
        target_user_id = row["user_id"]

        cur.execute("SELECT id FROM agent_friendships WHERE user_id=? AND friend_agent_id=? AND status='accepted'", (user_id, agent_id))
        if cur.fetchone():
            raise ValueError("已经是好友")

        cur.execute("SELECT id FROM agent_friendships WHERE user_id=? AND friend_agent_id=? AND status='pending'", (user_id, agent_id))
        if cur.fetchone():
            raise ValueError("请求已发送，等待对方接受")

        with db_cursor(commit=True) as cur2:
            cur2.execute("""
                INSERT INTO agent_friendships (user_id, friend_agent_id, target_user_id, status)
                VALUES (?, ?, ?, 'pending')
            """, (user_id, agent_id, target_user_id))
    return True

def get_received_friend_requests(user_id: int):
    with db_cursor() as cur:
        cur.execute("""
            SELECT af.id, af.user_id as requester_id, u.username as requester_name,
                   af.friend_agent_id, mc.name as agent_name
            FROM agent_friendships af
            JOIN users u ON af.user_id = u.id
            JOIN model_configs mc ON af.friend_agent_id = mc.id
            WHERE af.target_user_id = ? AND af.status = 'pending'
            ORDER BY af.created_at DESC
        """, (user_id,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]

def accept_friend_request(user_id: int, request_id: int):
    with db_cursor() as cur:
        cur.execute("SELECT id FROM agent_friendships WHERE id=? AND target_user_id=?", (request_id, user_id))
        if not cur.fetchone():
            raise PermissionError("无权处理此请求")
        with db_cursor(commit=True) as cur2:
            cur2.execute("UPDATE agent_friendships SET status='accepted' WHERE id=?", (request_id,))
    return True

def reject_friend_request(user_id: int, request_id: int):
    with db_cursor() as cur:
        cur.execute("SELECT id FROM agent_friendships WHERE id=? AND target_user_id=?", (request_id, user_id))
        if not cur.fetchone():
            raise PermissionError("无权处理此请求")
        with db_cursor(commit=True) as cur2:
            cur2.execute("UPDATE agent_friendships SET status='rejected' WHERE id=?", (request_id,))
    return True

def call_agent(user_id: int, agent_id: str, query: str):
    """调用好友智能体并结算积分（提供方 95%，平台 5%）"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT af.id, mc.user_id as provider_id, mc.price
            FROM agent_friendships af
            JOIN model_configs mc ON af.friend_agent_id = mc.id
            WHERE af.user_id=? AND af.friend_agent_id=? AND af.status='accepted'
        """, (user_id, agent_id))
        rel = cur.fetchone()
        if not rel:
            raise PermissionError("不是好友或无权调用")

        price = rel["price"] or 1.0
        cur.execute("SELECT credits FROM users WHERE id=?", (user_id,))
        user = cur.fetchone()
        if not user or user["credits"] < price:
            raise ValueError("积分不足")

        provider_income = price * 0.95   # 提供方获得 95%
        platform_fee = price * 0.05     # 平台手续费 5%

        with db_cursor(commit=True) as cur2:
            cur2.execute("UPDATE users SET credits = credits - ? WHERE id=?", (price, user_id))
            cur2.execute("UPDATE users SET credits = credits + ? WHERE id=?", (provider_income, rel["provider_id"]))
            # 平台手续费可以存入积分库或暂不处理
            cur2.execute("""
                INSERT INTO contribution_log (user_id, action, event_type, points, model_source, model_id, detail)
                VALUES (?, '调用好友智能体', 'friend', ?, 'friend', ?, ?)
            """, (user_id, -price, agent_id, f"支付给智能体所有者"))
            cur2.execute("""
                INSERT INTO contribution_log (user_id, action, event_type, points, model_source, model_id, detail)
                VALUES (?, '智能体被调用收入', 'friend', ?, 'friend', ?, ?)
            """, (rel["provider_id"], provider_income, agent_id, f"来自用户{user_id}的调用"))

    return {"status": "charged", "price": price, "provider_income": provider_income, "platform_fee": platform_fee}
