# core/services/pet_service.py
# 宠物系统服务：宠物生成、查询、喂养、进化、觉醒
import random
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from ..db import db_cursor


# 稀有度等级（从低到高）
RARITY_ORDER = ["C", "B", "A", "S", "SR", "SSR"]

# 阵营
CAMPS = ["植物", "海洋", "动物", "菌群", "飞行", "碳基", "硅基"]

# 属性
ELEMENTS = ["金", "木", "水", "火", "土", "光", "暗"]

# 技能携带数（基础）
SKILL_SLOTS_BY_RARITY = {
    "C": 2,
    "B": 3,
    "A": 3,
    "S": 4,
    "SR": 4,
    "SSR": 4
}

# 资源类型
RESOURCE_TYPES = ["阳光", "经验胶囊小", "经验胶囊中", "经验胶囊大", "晶石", "进化石", "强化石", "觉醒之心", "万能钥匙", "能量石"]


def _random_pet_name(rarity: str) -> str:
    """生成随机宠物名字"""
    prefixes = ["小", "幼", "星", "光", "暗", "岩", "冰", "炎", "风", "雷"]
    suffixes = ["灵", "兽", "龙", "精", "妖", "卫", "使", "王", "神", "影"]
    return random.choice(prefixes) + random.choice(suffixes)


def create_pet(
    user_id: int,
    rarity: str = "C",
    camp: Optional[str] = None,
    element: Optional[str] = None,
    pet_name: Optional[str] = None,
    source_task_id: Optional[int] = None
) -> Dict[str, Any]:
    """创建一只新宠物，返回宠物信息"""
    if rarity not in RARITY_ORDER:
        rarity = "C"
    camp = camp or random.choice(CAMPS)
    element = element or random.choice(ELEMENTS)
    pet_name = pet_name or _random_pet_name(rarity)
    skill_slots = SKILL_SLOTS_BY_RARITY.get(rarity, 2)

    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO pets
            (owner_user_id, pet_name, rarity, camp, element, level, exp, stage,
             skill_slots, current_skills, strength, hp, defense, source_task_id, created_at)
            VALUES (?, ?, ?, ?, ?, 1, 0, 0, ?, '[]', 5, 20, 3, ?, ?)
        """, (user_id, pet_name, rarity, camp, element, skill_slots,
              source_task_id, datetime.now().isoformat()))
        pet_id = cur.lastrowid

    return get_pet(pet_id)


def get_pet(pet_id: int) -> Optional[Dict[str, Any]]:
    """获取宠物详情"""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM pets WHERE id=?", (pet_id,))
        row = cur.fetchone()
    if not row:
        return None
    pet = dict(row)
    pet["current_skills"] = json.loads(pet.get("current_skills") or "[]")
    return pet


def list_user_pets(user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """获取用户所有宠物"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT * FROM pets WHERE owner_user_id=?
            ORDER BY
                CASE rarity
                    WHEN 'SSR' THEN 1
                    WHEN 'SR' THEN 2
                    WHEN 'S' THEN 3
                    WHEN 'A' THEN 4
                    WHEN 'B' THEN 5
                    WHEN 'C' THEN 6
                    ELSE 7
                END,
                level DESC
            LIMIT ?
        """, (user_id, limit))
        rows = cur.fetchall()

    pets = []
    for row in rows:
        pet = dict(row)
        pet["current_skills"] = json.loads(pet.get("current_skills") or "[]")
        pets.append(pet)
    return pets


def add_resource(user_id: int, resource_type: str, amount: int) -> int:
    """增加资源，返回最新数量"""
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO game_resources (owner_user_id, resource_type, amount, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(owner_user_id, resource_type)
            DO UPDATE SET amount = amount + ?, updated_at = ?
        """, (user_id, resource_type, amount, datetime.now().isoformat(),
              amount, datetime.now().isoformat()))

        cur.execute("""
            SELECT amount FROM game_resources
            WHERE owner_user_id=? AND resource_type=?
        """, (user_id, resource_type))
        row = cur.fetchone()
        return row["amount"] if row else amount


def get_resource(user_id: int, resource_type: str) -> int:
    """查询某种资源数量"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT amount FROM game_resources
            WHERE owner_user_id=? AND resource_type=?
        """, (user_id, resource_type))
        row = cur.fetchone()
    return row["amount"] if row else 0


def get_all_resources(user_id: int) -> Dict[str, int]:
    """获取用户所有资源"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT resource_type, amount FROM game_resources
            WHERE owner_user_id=?
        """, (user_id,))
        rows = cur.fetchall()
    return {row["resource_type"]: row["amount"] for row in rows}


def feed_pet(pet_id: int, user_id: int, exp_amount: int = 10) -> Dict[str, Any]:
    """
    喂养宠物，增加经验。经验满自动升级。
    简化规则：每升一级需要 level * 20 经验。
    """
    pet = get_pet(pet_id)
    if not pet:
        return {"success": False, "message": "宠物不存在"}
    if pet["owner_user_id"] != user_id:
        return {"success": False, "message": "无权操作该宠物"}

    new_exp = pet["exp"] + exp_amount
    new_level = pet["level"]
    exp_needed = new_level * 20

    while new_exp >= exp_needed:
        new_exp -= exp_needed
        new_level += 1
        exp_needed = new_level * 20

    # 升级同时提升属性
    strength = pet["strength"] + (new_level - pet["level"]) * 2
    hp = pet["hp"] + (new_level - pet["level"]) * 5
    defense = pet["defense"] + (new_level - pet["level"]) * 1

    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE pets SET level=?, exp=?, strength=?, hp=?, defense=?
            WHERE id=?
        """, (new_level, new_exp, strength, hp, defense, pet_id))

    return {
        "success": True,
        "pet_id": pet_id,
        "level": new_level,
        "exp": new_exp,
        "exp_needed": exp_needed,
        "strength": strength,
        "hp": hp,
        "defense": defense
    }


def evolve_pet(pet_id: int, user_id: int) -> Dict[str, Any]:
    """
    宠物进化：消耗进化石，提升稀有度。
    规则：C→B→A→S→SSR（逐级进化），成功率随等级递减。
    """
    pet = get_pet(pet_id)
    if not pet:
        return {"success": False, "message": "宠物不存在"}
    if pet["owner_user_id"] != user_id:
        return {"success": False, "message": "无权操作该宠物"}

    current_rarity = pet["rarity"]
    if current_rarity == "SSR":
        return {"success": False, "message": "已是最高稀有度"}

    # 进化消耗
    EVOLVE_COST = {
        "C": {"stones": 10, "success_rate": 0.80},
        "B": {"stones": 20, "success_rate": 0.70},
        "A": {"stones": 50, "success_rate": 0.60},
        "S": {"stones": 100, "success_rate": 0.40},
        "SR": {"stones": 200, "success_rate": 0.20},
    }

    cost = EVOLVE_COST.get(current_rarity)
    if not cost:
        return {"success": False, "message": "进化配置缺失"}

    stones = get_resource(user_id, "进化石")
    if stones < cost["stones"]:
        return {"success": False, "message": f"进化石不足，需要 {cost['stones']}，当前 {stones}"}

    # 扣除进化石
    add_resource(user_id, "进化石", -cost["stones"])

    # 判定成功
    success = random.random() < cost["success_rate"]
    next_rarity = RARITY_ORDER[RARITY_ORDER.index(current_rarity) + 1]

    if success:
        new_slots = SKILL_SLOTS_BY_RARITY.get(next_rarity, pet["skill_slots"])
        with db_cursor(commit=True) as cur:
            cur.execute("""
                UPDATE pets SET rarity=?, skill_slots=?, stage=stage+1
                WHERE id=?
            """, (next_rarity, new_slots, pet_id))
        return {
            "success": True,
            "pet_id": pet_id,
            "from_rarity": current_rarity,
            "to_rarity": next_rarity,
            "message": f"进化成功！{current_rarity} → {next_rarity}"
        }
    else:
        return {
            "success": False,
            "pet_id": pet_id,
            "from_rarity": current_rarity,
            "message": f"进化失败，消耗了 {cost['stones']} 进化石"
        }


def strengthen_pet(pet_id: int, user_id: int, attribute: str = "strength") -> Dict[str, Any]:
    """
    强化宠物：消耗强化石，提升指定属性。
    attribute: strength / hp / defense
    """
    pet = get_pet(pet_id)
    if not pet:
        return {"success": False, "message": "宠物不存在"}
    if pet["owner_user_id"] != user_id:
        return {"success": False, "message": "无权操作该宠物"}

    stones_needed = 5
    stones = get_resource(user_id, "强化石")
    if stones < stones_needed:
        return {"success": False, "message": f"强化石不足，需要 {stones_needed}"}

    add_resource(user_id, "强化石", -stones_needed)

    with db_cursor(commit=True) as cur:
        if attribute == "hp":
            cur.execute("UPDATE pets SET hp=hp+10 WHERE id=?", (pet_id,))
        elif attribute == "defense":
            cur.execute("UPDATE pets SET defense=defense+2 WHERE id=?", (pet_id,))
        else:
            cur.execute("UPDATE pets SET strength=strength+3 WHERE id=?", (pet_id,))

    updated = get_pet(pet_id)
    return {
        "success": True,
        "pet_id": pet_id,
        "attribute": attribute,
        "pet": updated
    }


def awaken_pet(pet_id: int, user_id: int) -> Dict[str, Any]:
    """
    宠物觉醒：消耗觉醒石，增加一个技能栏，概率成功有保底。
    """
    pet = get_pet(pet_id)
    if not pet:
        return {"success": False, "message": "宠物不存在"}
    if pet["owner_user_id"] != user_id:
        return {"success": False, "message": "无权操作该宠物"}

    if pet["skill_slots"] >= 6:
        return {"success": False, "message": "技能栏已满"}

    stones = get_resource(user_id, "觉醒之心")
    if stones < 1:
        return {"success": False, "message": "觉醒之心不足"}

    add_resource(user_id, "觉醒之心", -1)

    success = random.random() < 0.6  # 60% 成功率

    if success:
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE pets SET skill_slots=skill_slots+1 WHERE id=?", (pet_id,))
        return {
            "success": True,
            "pet_id": pet_id,
            "new_slots": pet["skill_slots"] + 1,
            "message": "觉醒成功！技能栏 +1"
        }
    else:
        return {
            "success": True,
            "pet_id": pet_id,
            "new_slots": pet["skill_slots"],
            "message": "觉醒失败，消耗了 1 个觉醒之心"
        }


def release_pet(pet_id: int, user_id: int) -> Dict[str, Any]:
    """放生宠物"""
    pet = get_pet(pet_id)
    if not pet:
        return {"success": False, "message": "宠物不存在"}
    if pet["owner_user_id"] != user_id:
        return {"success": False, "message": "无权操作该宠物"}

    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM pets WHERE id=?", (pet_id,))

    return {"success": True, "pet_id": pet_id, "message": "宠物已放生"}


def get_statistics(user_id: int) -> Dict[str, Any]:
    """获取用户宠物统计"""
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM pets WHERE owner_user_id=?", (user_id,))
        total = cur.fetchone()["cnt"]

        cur.execute("""
            SELECT rarity, COUNT(*) as cnt FROM pets
            WHERE owner_user_id=? GROUP BY rarity
        """, (user_id,))
        by_rarity = {row["rarity"]: row["cnt"] for row in cur.fetchall()}

    return {
        "total": total,
        "by_rarity": by_rarity
    }
