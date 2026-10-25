# core/services/base_service.py
# 基地设施服务：设施升级、产出结算、宠物任职
import math
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from ..db import db_cursor
from . import pet_service


# 设施配置表
FACILITY_CONFIG = {
    "补给站": {
        "output_resource": "能量石",
        "base_output_per_hour": 0.5,
        "max_level": 40,
        "upgrade_cost_resource": "阳光",
        "upgrade_cost_multiplier": 20,
        "required_camp": "菌群",
        "captain_camps": ["菌群", "碳基", "硅基"]
    },
    "采集站": {
        "output_resource": "阳光",
        "base_output_per_hour": 1.0,
        "max_level": 40,
        "upgrade_cost_resource": "能量石",
        "upgrade_cost_multiplier": 10,
        "required_camp": "植物",
        "captain_camps": ["植物", "碳基", "硅基"]
    },
    "进化站": {
        "output_resource": "进化石",
        "base_output_per_hour": 0.2,
        "max_level": 40,
        "upgrade_cost_resource": "能量石",
        "upgrade_cost_multiplier": 30,
        "required_camp": "动物",
        "captain_camps": ["动物", "碳基", "硅基"]
    },
    "强化站": {
        "output_resource": "强化石",
        "base_output_per_hour": 0.3,
        "max_level": 40,
        "upgrade_cost_resource": "能量石",
        "upgrade_cost_multiplier": 25,
        "required_camp": "飞行",
        "captain_camps": ["飞行", "碳基", "硅基"]
    },
    "结晶站": {
        "output_resource": "晶石",
        "base_output_per_hour": 0.5,
        "max_level": 40,
        "upgrade_cost_resource": "能量石",
        "upgrade_cost_multiplier": 15,
        "required_camp": "水域",
        "captain_camps": ["水域", "碳基", "硅基"]
    },
    "通讯站": {
        "output_resource": "探测器机会",
        "base_output_per_hour": 0.1,
        "max_level": 10,
        "upgrade_cost_resource": "阳光",
        "upgrade_cost_multiplier": 50,
        "required_camp": None,
        "captain_camps": []
    },
}

# 产出增长系数：每级增长 8%
OUTPUT_GROWTH = 0.08


def get_facility(owner_user_id: int, facility_type: str) -> Optional[Dict[str, Any]]:
    """获取单个设施"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT * FROM base_facilities
            WHERE owner_user_id=? AND facility_type=?
        """, (owner_user_id, facility_type))
        row = cur.fetchone()
    if not row:
        return None
    facility = dict(row)
    if facility.get("member_pet_ids"):
        try:
            facility["member_pet_ids"] = json.loads(facility["member_pet_ids"])
        except Exception:
            facility["member_pet_ids"] = []
    else:
        facility["member_pet_ids"] = []
    return facility


def list_facilities(owner_user_id: int) -> List[Dict[str, Any]]:
    """列出用户所有设施"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT * FROM base_facilities WHERE owner_user_id=?
            ORDER BY facility_type
        """, (owner_user_id,))
        rows = cur.fetchall()

    result = []
    for row in rows:
        f = dict(row)
        try:
            f["member_pet_ids"] = json.loads(f.get("member_pet_ids") or "[]")
        except Exception:
            f["member_pet_ids"] = []
        result.append(f)
    return result


def initialize_facilities(owner_user_id: int) -> None:
    """新用户首次进入基地时，初始化所有设施为0级"""
    with db_cursor(commit=True) as cur:
        for ftype in FACILITY_CONFIG.keys():
            cur.execute("""
                INSERT OR IGNORE INTO base_facilities
                (owner_user_id, facility_type, level, member_pet_ids, status, created_at)
                VALUES (?, ?, 0, '[]', 'idle', ?)
            """, (owner_user_id, ftype, datetime.now().isoformat()))


def get_upgrade_cost(owner_user_id: int, facility_type: str) -> Dict[str, Any]:
    """获取升级所需消耗"""
    if facility_type not in FACILITY_CONFIG:
        return {"success": False, "message": "未知设施"}

    config = FACILITY_CONFIG[facility_type]
    facility = get_facility(owner_user_id, facility_type)
    if not facility:
        return {"success": False, "message": "设施不存在"}

    current_level = facility["level"]
    if current_level >= config["max_level"]:
        return {"success": False, "message": "已达最高等级"}

    next_level = current_level + 1
    cost_resource = config["upgrade_cost_resource"]
    cost_amount = next_level * config["upgrade_cost_multiplier"]

    return {
        "success": True,
        "facility_type": facility_type,
        "current_level": current_level,
        "next_level": next_level,
        "cost_resource": cost_resource,
        "cost_amount": cost_amount
    }


def upgrade_facility(owner_user_id: int, facility_type: str) -> Dict[str, Any]:
    """升级设施"""
    cost_info = get_upgrade_cost(owner_user_id, facility_type)
    if not cost_info.get("success"):
        return cost_info

    cost_resource = cost_info["cost_resource"]
    cost_amount = cost_info["cost_amount"]

    current = pet_service.get_resource(owner_user_id, cost_resource)
    if current < cost_amount:
        return {"success": False, "message": f"{cost_resource}不足，需要 {cost_amount}，当前 {current}"}

    pet_service.add_resource(owner_user_id, cost_resource, -cost_amount)

    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE base_facilities
            SET level=level+1, last_produced_at=?
            WHERE owner_user_id=? AND facility_type=?
        """, (datetime.now().isoformat(), owner_user_id, facility_type))

    return {
        "success": True,
        "facility_type": facility_type,
        "new_level": cost_info["next_level"],
        "message": f"升级成功，当前 {cost_info['next_level']} 级"
    }


def _calc_output_rate(facility: Dict[str, Any], config: Dict[str, Any]) -> float:
    """
    计算设施每小时产出。
    产出 = 基础值 × (1 + 等级×0.08) × 宠物加成
    """
    level = facility["level"]
    if level == 0:
        return 0.0

    base = config["base_output_per_hour"]
    base_output = base * (1 + level * OUTPUT_GROWTH)

    # 宠物加成
    multiplier = 1.0
    captain_id = facility.get("captain_pet_id")
    members = facility.get("member_pet_ids") or []

    if captain_id:
        # 检查队长是否是符合条件的阵营
        captain = pet_service.get_pet(captain_id)
        if captain and captain.get("camp") in config.get("captain_camps", []):
            multiplier += 2.0  # 队长 +200%

    # 队员加成：每个成员 +50%
    multiplier += len(members) * 0.5

    return base_output * multiplier


def collect_output(owner_user_id: int, facility_type: str) -> Dict[str, Any]:
    """收取设施产出，基于上次收取到当前的时间差"""
    if facility_type not in FACILITY_CONFIG:
        return {"success": False, "message": "未知设施"}

    config = FACILITY_CONFIG[facility_type]
    facility = get_facility(owner_user_id, facility_type)
    if not facility:
        return {"success": False, "message": "设施不存在"}

    if facility["level"] == 0:
        return {"success": False, "message": "设施尚未建造"}

    now = datetime.now()
    last = facility.get("last_produced_at")
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
        except Exception:
            last_dt = now
    else:
        last_dt = now

    elapsed_hours = (now - last_dt).total_seconds() / 3600
    # 最多累计 12 小时（防止长期不登录爆产）
    elapsed_hours = min(elapsed_hours, 12)

    if elapsed_hours < 0.01:
        return {"success": False, "message": "产出尚未积累"}

    rate = _calc_output_rate(facility, config)
    produced = int(rate * elapsed_hours)

    if produced <= 0:
        return {"success": False, "message": "产出过少，请稍后再来"}

    resource = config["output_resource"]
    pet_service.add_resource(owner_user_id, resource, produced)

    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE base_facilities SET last_produced_at=?
            WHERE owner_user_id=? AND facility_type=?
        """, (now.isoformat(), owner_user_id, facility_type))

    return {
        "success": True,
        "facility_type": facility_type,
        "resource": resource,
        "amount": produced,
        "elapsed_hours": round(elapsed_hours, 2)
    }


def assign_captain(owner_user_id: int, facility_type: str, pet_id: int) -> Dict[str, Any]:
    """任命队长"""
    if facility_type not in FACILITY_CONFIG:
        return {"success": False, "message": "未知设施"}
    config = FACILITY_CONFIG[facility_type]

    pet = pet_service.get_pet(pet_id)
    if not pet:
        return {"success": False, "message": "宠物不存在"}
    if pet["owner_user_id"] != owner_user_id:
        return {"success": False, "message": "无权操作该宠物"}

    # 检查阵营是否符合
    if pet["camp"] not in config.get("captain_camps", []):
        return {"success": False, "message": f"该宠物阵营（{pet['camp']}）不能担任此设施队长，需要 {config['captain_camps']}"}

    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE base_facilities SET captain_pet_id=?
            WHERE owner_user_id=? AND facility_type=?
        """, (pet_id, owner_user_id, facility_type))

    return {"success": True, "facility_type": facility_type, "captain_pet_id": pet_id}


def assign_member(owner_user_id: int, facility_type: str, pet_id: int) -> Dict[str, Any]:
    """添加队员（最多3名）"""
    if facility_type not in FACILITY_CONFIG:
        return {"success": False, "message": "未知设施"}

    pet = pet_service.get_pet(pet_id)
    if not pet:
        return {"success": False, "message": "宠物不存在"}
    if pet["owner_user_id"] != owner_user_id:
        return {"success": False, "message": "无权操作该宠物"}

    facility = get_facility(owner_user_id, facility_type)
    members = facility.get("member_pet_ids") or []

    if len(members) >= 3:
        return {"success": False, "message": "队员已满（最多3名）"}
    if pet_id in members:
        return {"success": False, "message": "该宠物已在队伍中"}

    members.append(pet_id)

    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE base_facilities SET member_pet_ids=?
            WHERE owner_user_id=? AND facility_type=?
        """, (json.dumps(members), owner_user_id, facility_type))

    return {"success": True, "facility_type": facility_type, "member_pet_ids": members}


def remove_member(owner_user_id: int, facility_type: str, pet_id: int) -> Dict[str, Any]:
    """移除队员"""
    facility = get_facility(owner_user_id, facility_type)
    if not facility:
        return {"success": False, "message": "设施不存在"}

    members = facility.get("member_pet_ids") or []
    if pet_id not in members:
        return {"success": False, "message": "该宠物不在队伍中"}

    members.remove(pet_id)

    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE base_facilities SET member_pet_ids=?
            WHERE owner_user_id=? AND facility_type=?
        """, (json.dumps(members), owner_user_id, facility_type))

    return {"success": True, "facility_type": facility_type, "member_pet_ids": members}


def get_base_overview(owner_user_id: int) -> Dict[str, Any]:
    """基地总览：所有设施的等级、产出速率、任职情况"""
    initialize_facilities(owner_user_id)
    facilities = list_facilities(owner_user_id)

    overview = []
    for f in facilities:
        ftype = f["facility_type"]
        config = FACILITY_CONFIG.get(ftype)
        if not config:
            continue

        rate = _calc_output_rate(f, config)
        overview.append({
            "facility_type": ftype,
            "level": f["level"],
            "output_resource": config["output_resource"],
            "output_per_hour": round(rate, 2),
            "captain_pet_id": f.get("captain_pet_id"),
            "member_pet_ids": f.get("member_pet_ids", []),
            "next_level_cost": get_upgrade_cost(owner_user_id, ftype)
        })

    return {
        "facilities": overview,
        "resources": pet_service.get_all_resources(owner_user_id)
    }
