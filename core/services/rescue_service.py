# core/services/rescue_service.py
# 解救任务服务：兼容旧 rescue_tasks 和新的 yunchong_tasks
import asyncio
import json
import re
import openai
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from ..db import db_cursor
from .. import config, safety_scan
from . import quality_service
from . import pet_service
from . import model_service
from . import knowledge_service


client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
    timeout=40,
    max_retries=2
)
MODEL = config.MODEL_NAME

SEVERITY_TO_PET_LEVEL = {
    "low": "C",
    "medium": "A",
    "high": "SR"
}

STATUS_AVAILABLE = "available"
STATUS_IN_PROGRESS = "in_progress"
STATUS_RESCUED = "rescued"
STATUS_FAILED = "failed"
STATUS_ABANDONED = "abandoned"

REWARD_CONFIG = {
    "C": {"sunlight": 10, "exp_small": 2, "universal_key": 1},
    "B": {"sunlight": 20, "exp_small": 3, "universal_key": 1},
    "A": {"sunlight": 30, "exp_medium": 2, "universal_key": 1},
    "S": {"sunlight": 50, "exp_medium": 3, "universal_key": 1},
    "SR": {"sunlight": 80, "exp_large": 2, "universal_key": 2},
    "SSR": {"sunlight": 150, "exp_large": 3, "universal_key": 3},
}

PASSIVE_REWARD_PER_HIT = 1
PASSIVE_DAILY_LIMIT = 10

TASK_TIMEOUT_MINUTES = 30
GUARANTEE_FAIL_COUNT = 3


# ========== 表名映射 ==========
def _table_name(task_source: str) -> str:
    """根据任务来源返回表名"""
    if task_source == "yunchong":
        return "yunchong_tasks"
    return "rescue_tasks"


# ========== 基础查询（兼容双表） ==========
def get_task(task_id: int, task_source: str = "rescue") -> Optional[Dict[str, Any]]:
    table = _table_name(task_source)
    with db_cursor() as cur:
        if task_source == "yunchong":
            cur.execute(f"""
                SELECT t.*, qi.title as issue_title, qi.detail as issue_detail,
                       qi.severity, qi.source
                FROM {table} t
                LEFT JOIN quality_issues qi ON t.issue_id = qi.id
                WHERE t.id=?
            """, (task_id,))
        else:
            cur.execute(f"""
                SELECT rt.*, qi.title, qi.detail, qi.source, qi.severity
                FROM {table} rt
                JOIN quality_issues qi ON rt.issue_id = qi.id
                WHERE rt.id=?
            """, (task_id,))
        row = cur.fetchone()
    return dict(row) if row else None


# ========== 分析 ==========
async def analyze_task(
    task_id: int,
    user_id: int,
    agent_id: Optional[str] = None,
    previous_failure: Optional[str] = None,
    task_source: str = "rescue"
) -> Dict[str, Any]:
    table = _table_name(task_source)
    task = get_task(task_id, task_source)
    if not task:
        return {"success": False, "message": "任务不存在"}

    # 检查保底
    attempts = task.get("attempts", 0) or 0
    if attempts >= GUARANTEE_FAIL_COUNT:
        return await _guaranteed_success(task_id, user_id, task, task_source)

    # 标记分析中
    with db_cursor(commit=True) as cur:
        cur.execute(f"""
            UPDATE {table}
            SET status=?, attempts=attempts+1, status_detail=?
            WHERE id=?
        """, (STATUS_IN_PROGRESS, "分析中", task_id))

    # 构造任务描述
    if task_source == "yunchong":
        title = task["title"]
        detail = task.get("detail") or ""
    else:
        title = task["title"]
        detail = task.get("detail") or ""

    task_text = f"{title} {detail}"

    # 检索知识库（申诉时跳过复用）
    similar = None
    if not previous_failure:
        try:
            similar = knowledge_service.find_similar_solution(task_text)
        except Exception as e:
            print(f"[知识库] 检索失败: {e}")

    if similar:
        kb_id = similar["id"]
        solution = similar["solution"]
        with db_cursor(commit=True) as cur:
            cur.execute(f"""
                UPDATE {table}
                SET solution=?, reused_from_kb_id=?, status_detail=?
                WHERE id=?
            """, (solution, kb_id, "从知识库复用", task_id))
        knowledge_service.increment_hit_count(kb_id)
        _reward_contributor(similar.get("contributor_id"))
        return {
            "success": True,
            "task_id": task_id,
            "solution": solution,
            "source": "knowledge_base",
            "kb_id": kb_id,
            "similarity": similar.get("similarity", 0),
            "method": similar.get("method", ""),
            "used_api": similar.get("used_api", False)
        }

    # 调用智能体
    issue_text = f"标题：{title}\n描述：{detail or '无详细描述'}"
    try:
        solution = await _call_agent_for_solution(agent_id, user_id, issue_text, previous_failure)
    except Exception as e:
        return {"success": False, "message": f"智能体分析失败：{str(e)}"}

    risk = safety_scan.analyze_risk(solution)
    if risk["level"] == "high":
        return {"success": False, "message": f"方案存在风险：{risk['message']}"}

    with db_cursor(commit=True) as cur:
        cur.execute(f"""
            UPDATE {table}
            SET solution=?, status_detail=?
            WHERE id=?
        """, (solution, "方案已生成，等待验证", task_id))

    return {
        "success": True,
        "task_id": task_id,
        "solution": solution,
        "source": "agent",
        "is_appeal": bool(previous_failure)
    }


# ========== 保底成功 ==========
async def _guaranteed_success(task_id: int, user_id: int, task: Dict[str, Any], task_source: str) -> Dict[str, Any]:
    table = _table_name(task_source)
    now = datetime.now().isoformat()
    solution = f"[保底方案] 针对问题「{task['title']}」，经过多次尝试未通过验证，系统自动判定为已解决。"

    with db_cursor(commit=True) as cur:
        cur.execute(f"""
            UPDATE {table}
            SET status=?, rescued_at=?, solution=?,
                status_detail='保底成功', verification_result=?
            WHERE id=?
        """, (
            STATUS_RESCUED, now, solution,
            json.dumps({"passed": True, "reason": "保底机制", "score": 40}),
            task_id
        ))
        cur.execute("""
            UPDATE quality_issues SET status='cleaned', cleaned_at=? WHERE id=?
        """, (now, task["issue_id"]))

    kb_id = None
    try:
        kb_id = knowledge_service.add_to_knowledge_base(
            task=task["title"], solution=solution,
            contributor_id=user_id, source_task_id=task_id, quality_score=40
        )
    except Exception as e:
        print(f"[知识库] 保底回流失败: {e}")

    pet_level = task["pet_level"]
    pet = pet_service.create_pet(user_id=user_id, rarity=pet_level, source_task_id=task_id)
    reward_cfg = REWARD_CONFIG.get(pet_level, REWARD_CONFIG["C"])
    _grant_rewards(user_id, reward_cfg)

    return {
        "success": True,
        "task_id": task_id,
        "status": STATUS_RESCUED,
        "pet": {"id": pet["id"], "name": pet["pet_name"], "rarity": pet["rarity"],
                "camp": pet["camp"], "element": pet["element"]},
        "reward": reward_cfg,
        "verification": {"passed": True, "reason": "保底机制", "score": 40},
        "kb_id": kb_id,
        "is_guaranteed": True,
        "message": f"保底成功！获得 {pet_level} 级宠物「{pet['pet_name']}」"
    }


# ========== 验证 ==========
async def verify_and_complete(
    task_id: int,
    user_id: int,
    task_source: str = "rescue"
) -> Dict[str, Any]:
    table = _table_name(task_source)
    task = get_task(task_id, task_source)
    if not task:
        return {"success": False, "message": "任务不存在"}
    if task["status"] != STATUS_IN_PROGRESS:
        return {"success": False, "message": f"任务状态为 {task['status']}，无法验证"}
    if not task.get("solution"):
        return {"success": False, "message": "尚未生成方案"}

    try:
        verification = await _verify_solution(task)
    except Exception as e:
        return {"success": False, "message": f"验证失败：{str(e)}"}

    now = datetime.now().isoformat()

    if not verification["passed"]:
        with db_cursor(commit=True) as cur:
            cur.execute(f"""
                UPDATE {table}
                SET verification_result=?, status_detail=?
                WHERE id=?
            """, (json.dumps(verification, ensure_ascii=False),
                  f"验证失败：{verification.get('reason', '未知原因')}", task_id))

        try:
            _record_failure(task, verification, task_source)
        except Exception as e:
            print(f"[失败记录] 写入失败: {e}")

        comfort = _grant_comfort_reward(user_id, task.get("attempts", 0) or 0)
        return {
            "success": False,
            "message": f"验证失败：{verification.get('reason', '方案未通过验证')}",
            "verification": verification,
            "comfort_reward": comfort,
            "attempts": task.get("attempts", 0)
        }

    with db_cursor(commit=True) as cur:
        cur.execute(f"""
            UPDATE {table}
            SET status=?, rescued_at=?, verification_result=?, status_detail=?
            WHERE id=?
        """, (STATUS_RESCUED, now, json.dumps(verification, ensure_ascii=False), "解救成功", task_id))
        cur.execute("""
            UPDATE quality_issues SET status='cleaned', cleaned_at=? WHERE id=?
        """, (now, task["issue_id"]))

    kb_id = None
    if not task.get("reused_from_kb_id"):
        try:
            score = verification.get("score", 60)
            kb_id = knowledge_service.add_to_knowledge_base(
                task=task["title"], solution=task["solution"],
                contributor_id=user_id, source_task_id=task_id, quality_score=score
            )
        except Exception as e:
            print(f"[知识库] 回流失败: {e}")

    pet_level = task["pet_level"]
    pet = pet_service.create_pet(user_id=user_id, rarity=pet_level, source_task_id=task_id)
    reward_cfg = REWARD_CONFIG.get(pet_level, REWARD_CONFIG["C"])
    _grant_rewards(user_id, reward_cfg)

    return {
        "success": True,
        "task_id": task_id,
        "status": STATUS_RESCUED,
        "pet": {"id": pet["id"], "name": pet["pet_name"], "rarity": pet["rarity"],
                "camp": pet["camp"], "element": pet["element"]},
        "reward": reward_cfg,
        "verification": verification,
        "kb_id": kb_id,
        "message": f"解救成功！获得 {pet_level} 级宠物「{pet['pet_name']}」"
    }


# ========== 辅助函数（保持不变） ==========
def _grant_rewards(user_id: int, reward_cfg: Dict[str, int]):
    if reward_cfg.get("sunlight"):
        pet_service.add_resource(user_id, "阳光", reward_cfg["sunlight"])
    if reward_cfg.get("exp_small"):
        pet_service.add_resource(user_id, "经验胶囊小", reward_cfg["exp_small"])
    if reward_cfg.get("exp_medium"):
        pet_service.add_resource(user_id, "经验胶囊中", reward_cfg["exp_medium"])
    if reward_cfg.get("exp_large"):
        pet_service.add_resource(user_id, "经验胶囊大", reward_cfg["exp_large"])
    if reward_cfg.get("universal_key"):
        pet_service.add_resource(user_id, "万能钥匙", reward_cfg["universal_key"])


def _grant_comfort_reward(user_id: int, attempts: int) -> Dict[str, int]:
    if attempts <= 0:
        sunlight, exp_small = 5, 0
    elif attempts == 1:
        sunlight, exp_small = 5, 1
    else:
        sunlight, exp_small = 3, 0
    pet_service.add_resource(user_id, "阳光", sunlight)
    if exp_small > 0:
        pet_service.add_resource(user_id, "经验胶囊小", exp_small)
    return {"sunlight": sunlight, "exp_small": exp_small}


def _reward_contributor(contributor_id: Optional[int]):
    if not contributor_id:
        return
    try:
        from . import credit_service
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        with db_cursor() as cur:
            cur.execute("""
                SELECT COALESCE(SUM(points), 0) as total FROM contribution_log
                WHERE user_id=? AND event_type='passive_pollination' AND created_at >= ?
            """, (contributor_id, today_start))
            today_points = cur.fetchone()["total"]
        if today_points >= PASSIVE_DAILY_LIMIT:
            return
        credit_service.add_credit(
            user_id=contributor_id, amount=PASSIVE_REWARD_PER_HIT,
            action="方案被复用", detail=f"被动授粉 +{PASSIVE_REWARD_PER_HIT}",
            event_type="passive_pollination"
        )
    except Exception as e:
        print(f"[被动积分] 发放失败: {e}")


def _record_failure(task: Dict[str, Any], verification: Dict[str, Any], task_source: str):
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO failed_cases
            (task_id, issue_id, title, detail, solution, fail_reason,
             verification_result, severity, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task["id"], task.get("issue_id"), task["title"],
            task.get("detail", ""), task.get("solution", ""),
            verification.get("reason", ""),
            json.dumps(verification, ensure_ascii=False),
            task.get("difficulty", "medium"),
            datetime.now().isoformat()
        ))


async def _call_agent_for_solution(
    agent_id: Optional[str], user_id: int,
    issue_text: str, previous_failure: Optional[str] = None
) -> str:
    failure_hint = ""
    if previous_failure:
        failure_hint = f"""

【上一次验证失败原因】
{previous_failure}

请针对上述失败原因，重新给出更有针对性、更具体的方案。避免笼统的通用建议。
"""

    prompt = f"""你是一个问题解决专家。请针对以下问题给出具体的解决方案。

问题：
{issue_text}
{failure_hint}

要求：
1. 分析问题的根本原因
2. 给出具体的修复建议或方案
3. 方案要清晰、可执行、有针对性
4. 用中文回答，控制在 400 字以内

请给出方案："""

    if agent_id:
        try:
            model_config = model_service.get_model_config(agent_id, user_id)
            if model_config:
                solution = await model_service.call_model_with_config(model_config, prompt)
                return solution.strip()
        except Exception as e:
            print(f"调用用户智能体失败，回退到官方助手: {e}")

    resp = await asyncio.to_thread(
        client.chat.completions.create,
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1000
    )
    return resp.choices[0].message.content.strip()


async def _verify_solution(task: Dict[str, Any]) -> Dict[str, Any]:
    solution = (task.get("solution") or "").strip()
    rule_reason = []
    if len(solution) < 30:
        return {"passed": False, "reason": "方案内容过短", "score": 10}
    plan_keywords = ["方案", "建议", "修复", "原因", "根因", "步骤", "调整", "增加", "修改", "检查"]
    if not any(kw in solution for kw in plan_keywords):
        rule_reason.append("方案缺少明确的分析或建议")

    prompt = f"""请判断以下解决方案是否真正解决了问题。严格输出 JSON。

问题标题：{task['title']}
问题描述：{task.get('detail') or '无'}

解决方案：
{solution}

输出格式：
{{"passed": true, "reason": "通过原因", "score": 80}}
或
{{"passed": false, "reason": "未通过原因", "score": 30}}

只输出 JSON。"""

    try:
        resp = await asyncio.to_thread(
            client.chat.completions.create,
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0, max_tokens=500
        )
        raw = resp.choices[0].message.content
        if not raw:
            raise ValueError("模型返回内容为空")
        raw = raw.strip()
        raw = re.sub(r'^```[a-z]*\n?', '', raw)
        raw = re.sub(r'\n?```$', '', raw).strip()
        match = re.search(r'\{[\s\S]*\}', raw)
        if not match:
            raise ValueError(f"未找到 JSON: {raw[:100]}")
        result = json.loads(match.group())
        passed = bool(result.get("passed", False))
        score = int(result.get("score", 0))
        reason = result.get("reason", "")
        if score < 60:
            passed = False
        if rule_reason:
            passed = False
            reason = "；".join(rule_reason) + ("；" + reason if reason else "")
        return {"passed": passed, "reason": reason or ("方案通过验证" if passed else "方案未通过验证"), "score": score}
    except Exception as e:
        print(f"[验证器] LLM 验证失败，降级为规则判断: {e}")
        if rule_reason:
            return {"passed": False, "reason": "；".join(rule_reason), "score": 30}
        return {"passed": True, "reason": f"方案通过基础验证", "score": 60}
# ========== 超时回收（兼容旧调用） ==========
def reclaim_expired_tasks(timeout_minutes: int = 30):
    """回收超时的旧表 rescue_tasks（兼容保留）"""
    cutoff = (datetime.now() - timedelta(minutes=timeout_minutes)).isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE rescue_tasks
            SET status='available',
                rescued_by_user_id=NULL,
                assigned_agent_id=NULL,
                solution=NULL,
                attempts=0,
                status_detail='超时回收',
                created_at=?
            WHERE status='in_progress'
              AND created_at < ?
        """, (datetime.now().isoformat(), cutoff))
        count = cur.rowcount
    return {"reclaimed": count}
