# core/services/group_service.py
from ..db import db_cursor


def create_group(name: str, owner_id: int):
    """创建群聊，返回群 ID"""
    with db_cursor(commit=True) as cur:
        cur.execute("INSERT INTO groups (name, owner_id) VALUES (?, ?)", (name, owner_id))
        group_id = cur.lastrowid
        cur.execute("INSERT INTO group_members (group_id, user_id, role) VALUES (?, ?, 'owner')", (group_id, owner_id))
        return group_id


def invite_to_group(group_id: int, inviter_id: int, invitee: str):
    """邀请用户或智能体加入群聊。invitee 可以是用户名、SASES ID、智能体 ID 或智能体名称。"""
    with db_cursor() as cur:
        # 检查邀请者是否在群中
        cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, inviter_id))
        if not cur.fetchone():
            return False, "邀请者不是群成员"

        # 先尝试匹配用户
        cur.execute("SELECT id FROM users WHERE username=? OR sases_id=?", (invitee, invitee))
        user = cur.fetchone()
        if user:
            target_user_id = user["id"]
            cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, target_user_id))
            if cur.fetchone():
                return False, "用户已在群中"
            with db_cursor(commit=True) as cur2:
                cur2.execute("INSERT INTO group_members (group_id, user_id) VALUES (?, ?)", (group_id, target_user_id))
            return True, "邀请用户成功"

        # 尝试匹配智能体（仅限邀请者自己的智能体）
        cur.execute("""
            SELECT id FROM model_configs
            WHERE (id=? OR name=?) AND user_id=?
        """, (invitee, invitee, inviter_id))
        agent = cur.fetchone()
        if agent:
            agent_id = agent["id"]
            cur.execute("SELECT id FROM group_members WHERE group_id=? AND agent_id=?", (group_id, agent_id))
            if cur.fetchone():
                return False, "智能体已在群中"
            with db_cursor(commit=True) as cur2:
                cur2.execute("INSERT INTO group_members (group_id, agent_id, role) VALUES (?, ?, 'agent')", (group_id, agent_id))
            return True, "邀请智能体成功"

        return False, "找不到该用户或智能体，或智能体不属于你"


def list_user_groups(user_id: int):
    """获取用户所在的群聊列表"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT g.id, g.name, g.owner_id,
                   (SELECT COUNT(*) FROM group_members gm WHERE gm.group_id = g.id) as member_count
            FROM groups g
            JOIN group_members gm2 ON g.id = gm2.group_id
            WHERE gm2.user_id = ?
            ORDER BY g.created_at DESC
        """, (user_id,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def get_group_messages(group_id: int, user_id: int):
    """获取群聊消息（需为群成员）"""
    with db_cursor() as cur:
        cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
        if not cur.fetchone():
            return None
        cur.execute("""
            SELECT m.id, m.content, m.created_at,
                   CASE WHEN m.sender_agent_id IS NOT NULL THEN mc.name
                        ELSE u.username END as sender_name,
                   m.sender_id, m.sender_agent_id
            FROM group_messages m
            LEFT JOIN users u ON m.sender_id = u.id
            LEFT JOIN model_configs mc ON m.sender_agent_id = mc.id
            WHERE m.group_id = ?
            ORDER BY m.created_at ASC
            LIMIT 100
        """, (group_id,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def send_group_message(group_id: int, sender_id: int, content: str, sender_agent_id: str = None):
    """发送群聊消息，可为用户或智能体"""
    with db_cursor(commit=True) as cur:
        if sender_agent_id:
            # 验证智能体是否为群成员
            cur.execute("SELECT id FROM group_members WHERE group_id=? AND agent_id=?", (group_id, sender_agent_id))
            if not cur.fetchone():
                return False
            cur.execute("INSERT INTO group_messages (group_id, sender_agent_id, content) VALUES (?, ?, ?)", (group_id, sender_agent_id, content))
        else:
            # 验证用户是否为群成员
            cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, sender_id))
            if not cur.fetchone():
                return False
            cur.execute("INSERT INTO group_messages (group_id, sender_id, content) VALUES (?, ?, ?)", (group_id, sender_id, content))
        return True


def list_group_members(group_id: int):
    """获取群成员列表，包括用户和智能体"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT gm.user_id, gm.agent_id, gm.role,
                   COALESCE(u.username, mc.name) as display_name,
                   CASE WHEN gm.agent_id IS NOT NULL THEN 'agent' ELSE 'user' END as member_type
            FROM group_members gm
            LEFT JOIN users u ON gm.user_id = u.id
            LEFT JOIN model_configs mc ON gm.agent_id = mc.id
            WHERE gm.group_id = ?
        """, (group_id,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def get_group_credits(group_id: int):
    """获取群积分（暂返回0，后续可统计）"""
    # 实际中可以从群积分表或贡献日志统计，这里简化
    return 0.0


def remove_member_from_group(group_id: int, remover_id: int, member_identifier: str):
    """移除群成员（仅群主可操作）"""
    with db_cursor() as cur:
        # 检查操作者是否为群主
        cur.execute("SELECT owner_id FROM groups WHERE id=?", (group_id,))
        group = cur.fetchone()
        if not group or group["owner_id"] != remover_id:
            return False, "只有群主可以移除成员"

        # 根据标识查找成员（支持用户 ID、智能体 ID、用户名）
        cur.execute("""
            SELECT id FROM group_members
            WHERE group_id=?
              AND (CAST(user_id AS TEXT)=? OR agent_id=? OR user_id IN (SELECT id FROM users WHERE username=?))
        """, (group_id, member_identifier, member_identifier, member_identifier))
        member = cur.fetchone()
        if not member:
            return False, "成员不存在"

        with db_cursor(commit=True) as cur2:
            cur2.execute("DELETE FROM group_members WHERE id=?", (member["id"],))
        return True, "移除成功"
