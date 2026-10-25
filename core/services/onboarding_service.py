# core/services/onboarding_service.py
# 新手引导服务：管理用户前 7 天的功能解锁进度
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from ..db import db_cursor


# 7天引导配置
ONBOARDING_STEPS = {
    1: {
        "title": "发送第一条消息",
        "desc": "在消息页点击任意会话，发送一条消息",
        "action": "send_message",
        "hint": "试试输入「你好」"
    },
    2: {
        "title": "创建智能体",
        "desc": "进入「我的 → 模型管理」，添加一个 API Key 智能体",
        "action": "create_agent",
        "hint": "推荐使用 DeepSeek"
    },
    3: {
        "title": "执行一次指令",
        "desc": "在自由模式聊天窗口输入「执行：dir」",
        "action": "execute_command",
        "hint": "体验指令模式"
    },
    4: {
        "title": "进入智维空间",
        "desc": "在发现页点击「智维空间」，查看官方节点",
        "action": "open_wisdom",
        "hint": "你的数字世界入口"
    },
    5: {
        "title": "完成一次解救任务",
        "desc": "在智维空间点击「解救任务」，接取并完成一次",
        "action": "complete_rescue",
        "hint": "解救成功后获得宠物"
    },
    6: {
        "title": "培养一只宠物",
        "desc": "在智维空间点击「宠物养成」，喂养或进化一只宠物",
        "action": "feed_pet",
        "hint": "宠物会陪你探索宇宙"
    },
    7: {
        "title": "升级一个基地设施",
        "desc": "在智维空间点击「我的基地」，升级任意一个设施",
        "action": "upgrade_facility",
        "hint": "基地会持续产出资源"
    }
}


def get_user_onboarding(user_id: int) -> Dict[str, Any]:
    """获取用户当前引导状态"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT onboarding_day, onboarding_completed, onboarding_started_at
            FROM users WHERE id=?
        """, (user_id,))
        row = cur.fetchone()

    if not row:
        return {"success": False, "message": "用户不存在"}

    day = row["onboarding_day"] or 1
    completed_raw = row["onboarding_completed"] or "[]"
    try:
        completed = json.loads(completed_raw)
    except Exception:
        completed = []

    started_at = row["onboarding_started_at"]

    # 当前应显示的任务
    current_step = ONBOARDING_STEPS.get(day)

    # 是否已完成所有引导
    all_done = day > 7

    return {
        "success": True,
        "current_day": day,
        "completed_days": completed,
        "current_step": current_step,
        "is_finished": all_done,
        "started_at": started_at
    }


def complete_onboarding_step(user_id: int, action: str) -> Dict[str, Any]:
    """
    用户完成某个动作时调用。
    如果 action 与当前应完成的任务匹配，则解锁下一天。
    """
    with db_cursor() as cur:
        cur.execute("""
            SELECT onboarding_day, onboarding_completed, onboarding_started_at
            FROM users WHERE id=?
        """, (user_id,))
        row = cur.fetchone()

    if not row:
        return {"success": False, "message": "用户不存在"}

    day = row["onboarding_day"] or 1
    completed_raw = row["onboarding_completed"] or "[]"
    try:
        completed = json.loads(completed_raw)
    except Exception:
        completed = []

    started_at = row["onboarding_started_at"]
    if not started_at:
        started_at = datetime.now().isoformat()

    # 如果已经完成所有引导，不再处理
    if day > 7:
        return {
            "success": True,
            "advanced": False,
            "message": "已完成所有引导"
        }

    current_step = ONBOARDING_STEPS.get(day)
    if not current_step:
        return {"success": False, "message": "无效的引导天数"}

    # 检查动作是否匹配
    if current_step["action"] != action:
        return {
            "success": True,
            "advanced": False,
            "message": f"当前任务是「{current_step['title']}」"
        }

    # 匹配成功，解锁下一天
    new_day = day + 1
    completed.append(day)

    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE users
            SET onboarding_day=?, onboarding_completed=?, onboarding_started_at=?
            WHERE id=?
        """, (new_day, json.dumps(completed), started_at, user_id))

    next_step = ONBOARDING_STEPS.get(new_day)
    return {
        "success": True,
        "advanced": True,
        "new_day": new_day,
        "completed_days": completed,
        "next_step": next_step,
        "message": f"完成第 {day} 天任务，解锁第 {new_day} 天"
    }


def reset_onboarding(user_id: int) -> Dict[str, Any]:
    """重置引导（用于测试）"""
    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE users
            SET onboarding_day=1, onboarding_completed='[]', onboarding_started_at=?
            WHERE id=?
        """, (datetime.now().isoformat(), user_id))

    return {"success": True, "message": "引导已重置"}


def get_all_steps() -> Dict[int, Dict[str, Any]]:
    """获取所有引导步骤定义"""
    return ONBOARDING_STEPS
