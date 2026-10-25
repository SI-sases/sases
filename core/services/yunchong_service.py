# core/services/yunchong_service.py
# 云宠战役核心服务：地图任务刷新、接取、放弃、能量扣费
import random
import uuid
import math
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from ..db import db_cursor
from . import quality_service
from . import credit_service


# ========== 刷新配置 ==========
REFRESH_INTERVAL_MINUTES = 15
TASKS_PER_BATCH_MIN = 8
TASKS_PER_BATCH_MAX = 12

# 距离段配置（含概率、能量、宠物稀有度概率分布）
DISTANCE_SEGMENTS = [
    {
        "key": "near",
        "max_meters": 100,
        "energy_cost": 0,
        "ratio": 0.40,
        "pet_weights": {"C": 70, "B": 25, "A": 5}
    },
    {
        "key": "mid",
        "max_meters": 500,
        "energy_cost": 5,
        "ratio": 0.30,
        "pet_weights": {"C": 30, "B": 40, "A": 25, "S": 5}
    },
    {
        "key": "far",
        "max_meters": 1000,
        "energy_cost": 10,
        "ratio": 0.20,
        "pet_weights": {"B": 20, "A": 35, "S": 35, "SR": 10}
    },
    {
        "key": "remote",
        "max_meters": 5000,
        "energy_cost": 15,
        "ratio": 0.10,
        "pet_weights": {"A": 20, "S": 40, "SR": 30, "SSR": 10}
    },
]

# 严重程度到宠物稀有度的基础映射
SEVERITY_TO_PET_LEVEL = {
    "low": "C",
    "medium": "A",
    "high": "SR"
}

STATUS_AVAILABLE = "available"
STATUS_IN_PROGRESS = "in_progress"
STATUS_RESCUED = "rescued"
STATUS_FAILED = "failed"
STATUS_EXPIRED = "expired"

# 官方助手每日免费次数
OFFICIAL_AGENT_FREE_DAILY = 3
OFFICIAL_AGENT_COST_PER_USE = 10


# ========== 刷新相关 ==========
def get_refresh_info(user_id: int) -> Dict[str, Any]:
    """获取用户的刷新信息（上次刷新时间、下次刷新倒计时）"""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM yunchong_refresh_log WHERE user_id=?", (user_id,))
        row = cur.fetchone()

    if not row:
        return {
            "last_refresh_at": None,
            "next_refresh_seconds": 0,
            "current_batch_id": None
        }

    last_refresh = row["last_refresh_at"]
    current_batch = row["current_batch_id"]

    try:
        last_dt = datetime.fromisoformat(last_refresh)
        next_dt = last_dt + timedelta(minutes=REFRESH_INTERVAL_MINUTES)
        remaining = int((next_dt - datetime.now()).total_seconds())
        remaining = max(0, remaining)
    except Exception:
        remaining = 0

    return {
        "last_refresh_at": last_refresh,
        "next_refresh_seconds": remaining,
        "current_batch_id": current_batch
    }


def needs_refresh(user_id: int) -> bool:
    """检查用户是否需要刷新任务批次"""
    info = get_refresh_info(user_id)
    if not info["current_batch_id"]:
        return True
    return info["next_refresh_seconds"] <= 0


def refresh_user_tasks(user_id: int) -> Dict[str, Any]:
    """
    刷新用户的任务批次。
    1. 将旧批次中 available 的任务标记为 expired
    2. 生成新批次
    """
    # 1. 旧任务过期
    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE yunchong_tasks
            SET status='expired', status_detail='批次过期'
            WHERE owner_user_id=? AND status='available'
        """, (user_id,))
        expired_count = cur.rowcount

    # 2. 生成新批次
    batch_id = str(uuid.uuid4())[:8]
    task_count = random.randint(TASKS_PER_BATCH_MIN, TASKS_PER_BATCH_MAX)
    now = datetime.now()
    expires_at = (now + timedelta(minutes=REFRESH_INTERVAL_MINUTES)).isoformat()

    # 准备任务池
    issue_pool = _fetch_available_issues(task_count * 2)
    template_pool = _get_template_tasks()
    used_titles = set()
    created = 0

    for i in range(task_count):
        # 选择距离段
        segment = _pick_distance_segment()
        # 选择宠物稀有度
        pet_level = _pick_pet_level(segment["pet_weights"])
        # 计算距离
        distance = random.randint(10, segment["max_meters"])
        # 计算坐标
        angle = random.random() * 2 * math.pi
        longitude = math.cos(angle) * distance / 1000
        latitude = math.sin(angle) * distance / 1000

        # 选择任务来源：优先 issue，其次模板
        title = None
        detail = ""
        issue_id = None

        while issue_pool:
            candidate = issue_pool.pop(0)
            if candidate["title"] not in used_titles:
                title = candidate["title"]
                detail = candidate.get("detail", "")
                issue_id = candidate["id"]
                used_titles.add(title)
                break

        if not title:
            for _ in range(10):
                tmpl = random.choice(template_pool)
                if tmpl["title"] not in used_titles:
                    title = tmpl["title"]
                    detail = tmpl["detail"]
                    used_titles.add(title)
                    break
            if not title:
                title = f"解救任务 #{i+1}"
                detail = "一个等待解决的系统问题"

        # 写入任务
        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO yunchong_tasks
                (owner_user_id, issue_id, title, detail, difficulty, pet_level,
                 status, longitude, latitude, distance_meters, energy_cost,
                 batch_id, refreshed_at, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'available', ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, issue_id, title, detail,
                _pet_level_to_difficulty(pet_level), pet_level,
                longitude, latitude, distance, segment["energy_cost"],
                batch_id, now.isoformat(), expires_at, now.isoformat()
            ))
            created += 1

    # 3. 更新刷新日志
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO yunchong_refresh_log (user_id, last_refresh_at, current_batch_id, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                last_refresh_at=excluded.last_refresh_at,
                current_batch_id=excluded.current_batch_id,
                updated_at=excluded.updated_at
        """, (user_id, now.isoformat(), batch_id, now.isoformat()))

    return {
        "success": True,
        "batch_id": batch_id,
        "created": created,
        "expired": expired_count,
        "expires_at": expires_at,
        "next_refresh_seconds": REFRESH_INTERVAL_MINUTES * 60
    }


# ========== 任务查询 ==========
def list_user_tasks(user_id: int) -> List[Dict[str, Any]]:
    """列出用户的当前批次任务"""
    if needs_refresh(user_id):
        refresh_user_tasks(user_id)

    with db_cursor() as cur:
        cur.execute("""
            SELECT id, title, detail, difficulty, pet_level, status,
                   longitude, latitude, distance_meters, energy_cost,
                   batch_id, attempts, created_at
            FROM yunchong_tasks
            WHERE owner_user_id=? AND status='available'
            ORDER BY distance_meters ASC
        """, (user_id,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def get_task(task_id: int) -> Optional[Dict[str, Any]]:
    """获取任务详情"""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM yunchong_tasks WHERE id=?", (task_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def get_task_with_issue(task_id: int) -> Optional[Dict[str, Any]]:
    """获取任务详情，含 issue 信息"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT t.*, qi.title as issue_title, qi.detail as issue_detail,
                   qi.severity, qi.source
            FROM yunchong_tasks t
            LEFT JOIN quality_issues qi ON t.issue_id = qi.id
            WHERE t.id=?
        """, (task_id,))
        row = cur.fetchone()
    return dict(row) if row else None


# ========== 接取与放弃 ==========
def accept_task(task_id: int, user_id: int) -> Dict[str, Any]:
    """接取任务，扣除能量（种子积分）"""
    task = get_task(task_id)
    if not task:
        return {"success": False, "message": "任务不存在"}
    if task["owner_user_id"] != user_id:
        return {"success": False, "message": "无权操作该任务"}
    if task["status"] != STATUS_AVAILABLE:
        return {"success": False, "message": f"任务状态为 {task['status']}，无法接取"}

    # 检查雷达
    has_radar = has_active_radar(user_id)
    energy_cost = task["energy_cost"]
    if has_radar and task["distance_meters"] <= 1500:
        energy_cost = 0

    # 扣积分
    if energy_cost > 0:
        balance = credit_service.get_balance(user_id)
        if balance is None or balance < energy_cost:
            return {
                "success": False,
                "message": f"积分不足，需要 {energy_cost}，当前 {balance or 0}"
            }
        credit_service.add_credit(
            user_id=user_id,
            amount=-energy_cost,
            action="云宠战役任务",
            detail=f"接取任务：{task['title']}",
            event_type="yunchong_energy"
        )

    # 更新状态
    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE yunchong_tasks
            SET status=?, attempts=attempts+1, status_detail=?
            WHERE id=?
        """, (STATUS_IN_PROGRESS, "已接取，等待分析", task_id))

    return {
        "success": True,
        "task_id": task_id,
        "energy_cost": energy_cost,
        "status": STATUS_IN_PROGRESS
    }


def abandon_task(task_id: int, user_id: int) -> Dict[str, Any]:
    """放弃任务"""
    task = get_task(task_id)
    if not task:
        return {"success": False, "message": "任务不存在"}
    if task["owner_user_id"] != user_id:
        return {"success": False, "message": "无权操作该任务"}
    if task["status"] != STATUS_IN_PROGRESS:
        return {"success": False, "message": f"任务状态为 {task['status']}，无法放弃"}

    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE yunchong_tasks
            SET status='available', status_detail='用户放弃'
            WHERE id=?
        """, (task_id,))

    return {"success": True, "task_id": task_id, "message": "任务已释放"}


# ========== 官方助手计费 ==========
def check_official_agent_usage(user_id: int) -> Dict[str, Any]:
    """检查官方助手今日使用情况"""
    today = datetime.now().date().isoformat()
    with db_cursor() as cur:
        cur.execute("SELECT * FROM yunchong_official_agent_usage WHERE user_id=?", (user_id,))
        row = cur.fetchone()

    if not row or row["reset_date"] != today:
        return {
            "used_today": 0,
            "remaining_free": OFFICIAL_AGENT_FREE_DAILY,
            "need_pay": False
        }

    used = row["used_today"]
    remaining = max(0, OFFICIAL_AGENT_FREE_DAILY - used)
    return {
        "used_today": used,
        "remaining_free": remaining,
        "need_pay": remaining <= 0
    }


def consume_official_agent(user_id: int) -> Dict[str, Any]:
    """
    使用一次官方助手。
    免费次数内不扣算力，超出后扣 10 算力。
    """
    today = datetime.now().date().isoformat()
    with db_cursor() as cur:
        cur.execute("SELECT * FROM yunchong_official_agent_usage WHERE user_id=?", (user_id,))
        row = cur.fetchone()

    if not row or row["reset_date"] != today:
        # 今天第一次使用
        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO yunchong_official_agent_usage (user_id, used_today, reset_date, updated_at)
                VALUES (?, 1, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    used_today=1, reset_date=excluded.reset_date, updated_at=excluded.updated_at
            """, (user_id, today, datetime.now().isoformat()))
        return {"success": True, "free": True, "used_today": 1, "remaining_free": OFFICIAL_AGENT_FREE_DAILY - 1}

    used = row["used_today"]
    if used < OFFICIAL_AGENT_FREE_DAILY:
        # 还有免费次数
        with db_cursor(commit=True) as cur:
            cur.execute("""
                UPDATE yunchong_official_agent_usage
                SET used_today=used_today+1, updated_at=?
                WHERE user_id=?
            """, (datetime.now().isoformat(), user_id))
        return {"success": True, "free": True, "used_today": used + 1, "remaining_free": OFFICIAL_AGENT_FREE_DAILY - used - 1}
    else:
        # 超出免费次数，扣算力
        from . import compute_service
        balance = compute_service.get_balance(user_id)
        if balance < OFFICIAL_AGENT_COST_PER_USE:
            return {
                "success": False,
                "message": f"算力不足，需要 {OFFICIAL_AGENT_COST_PER_USE}，当前 {balance}"
            }
        result = compute_service.deduct_compute(
            user_id=user_id,
            amount=OFFICIAL_AGENT_COST_PER_USE,
            service_key="official_agent",
            detail="云宠战役官方助手"
        )
        if not result["success"]:
            return result

        with db_cursor(commit=True) as cur:
            cur.execute("""
                UPDATE yunchong_official_agent_usage
                SET used_today=used_today+1, updated_at=?
                WHERE user_id=?
            """, (datetime.now().isoformat(), user_id))

        return {
            "success": True,
            "free": False,
            "consumed_compute": OFFICIAL_AGENT_COST_PER_USE,
            "used_today": used + 1,
            "remaining_free": 0
        }


# ========== 雷达道具 ==========
def has_active_radar(user_id: int) -> bool:
    """检查用户是否有生效的雷达"""
    with db_cursor() as cur:
        cur.execute("SELECT expires_at FROM yunchong_radar WHERE user_id=?", (user_id,))
        row = cur.fetchone()
    if not row or not row["expires_at"]:
        return False
    try:
        exp = datetime.fromisoformat(row["expires_at"])
        return exp > datetime.now()
    except Exception:
        return False


# ========== 内部辅助函数 ==========
def _fetch_available_issues(limit: int = 20) -> List[Dict[str, Any]]:
    """从 quality_issues 中获取待处理的问题"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, title, detail, severity, source
            FROM quality_issues
            WHERE status='pending'
            ORDER BY id ASC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def _pick_distance_segment() -> Dict[str, Any]:
    """按概率随机选一个距离段"""
    roll = random.random()
    cumulative = 0
    for seg in DISTANCE_SEGMENTS:
        cumulative += seg["ratio"]
        if roll <= cumulative:
            return seg
    return DISTANCE_SEGMENTS[0]


def _pick_pet_level(weights: Dict[str, int]) -> str:
    """按权重随机选宠物稀有度"""
    levels = list(weights.keys())
    weights_list = [weights[l] for l in levels]
    return random.choices(levels, weights=weights_list, k=1)[0]


def _pet_level_to_difficulty(pet_level: str) -> str:
    """宠物稀有度映射到难度"""
    if pet_level in ("C", "B"):
        return "low"
    elif pet_level in ("A", "S"):
        return "medium"
    else:
        return "high"


def _get_template_tasks() -> List[Dict[str, str]]:
    """获取模板任务池（当 quality_issues 为空时的兜底）"""
    return [
        {"title": "修复一个排序函数的边界条件错误", "detail": "排序函数在数组为空或只有一个元素时出现异常"},
        {"title": "修正文档中的参数说明错误", "detail": "函数文档中的参数说明与实际实现不一致"},
        {"title": "优化一个递归函数的性能", "detail": "递归函数在深度较大时出现栈溢出或超时"},
        {"title": "检查一段代码是否存在注入风险", "detail": "用户输入未经过滤直接用于数据库查询"},
        {"title": "清洗一批包含异常值的数据", "detail": "数据集中包含明显的异常值，需要过滤或修正"},
        {"title": "修复一个网络请求的超时处理", "detail": "网络请求未设置超时，导致长时间阻塞"},
        {"title": "改进一段日志输出的可读性", "detail": "日志输出缺少关键信息，难以定位问题"},
        {"title": "修复一个并发场景下的竞态条件", "detail": "多线程访问共享资源时出现数据不一致"},
        {"title": "简化一段复杂的条件判断逻辑", "detail": "过多的嵌套条件导致代码可读性差"},
        {"title": "补充一个缺失的错误处理分支", "detail": "某处异常未捕获，导致程序崩溃"},
        {"title": "统一代码中的命名风格", "detail": "变量和函数命名风格不一致，影响可维护性"},
        {"title": "修复一个分页查询的边界问题", "detail": "分页查询在最后一页时返回错误数量"},
        {"title": "改进一段正则表达式的效率", "detail": "正则表达式在大文本下性能下降明显"},
        {"title": "修复一个缓存失效的逻辑错误", "detail": "缓存未按预期失效，导致返回陈旧数据"},
        {"title": "优化一段循环内的重复计算", "detail": "循环中重复计算不变的值，浪费性能"},
    ]
