# core/services/pollination_service.py
from datetime import datetime, timedelta
from ..db import db_cursor
from .. import safety_scan
from . import credit_service

# 授粉积分规则
POLLINATION_REWARD_BASIC = 1
POLLINATION_REWARD_PROFESSIONAL = 2
POLLINATION_REWARD_EXTREME = 3
POLLINATION_DAILY_LIMIT = 100

# 挑坏果子积分规则
FALSIFY_REWARD = 5
FALSIFY_DAILY_LIMIT = 50


def get_today_pollination_points(user_id: int) -> int:
    """获取用户今日已获得的授粉积分总量"""
    today_start = datetime.combine(datetime.today(), datetime.min.time()).isoformat()
    with db_cursor() as cur:
        cur.execute("""
            SELECT COALESCE(SUM(points), 0) as total FROM contribution_log
            WHERE user_id=? AND event_type='pollination' AND created_at >= ?
        """, (user_id, today_start))
        row = cur.fetchone()
        return row["total"] if row else 0


def get_today_falsify_points(user_id: int) -> int:
    """获取用户今日已获得的挑坏果子积分总量"""
    today_start = datetime.combine(datetime.today(), datetime.min.time()).isoformat()
    with db_cursor() as cur:
        cur.execute("""
            SELECT COALESCE(SUM(points), 0) as total FROM contribution_log
            WHERE user_id=? AND event_type='falsify' AND created_at >= ?
        """, (user_id, today_start))
        row = cur.fetchone()
        return row["total"] if row else 0


CHAT_ONLY = {'你好', '在吗', '嗯', '哦', '好', '谢谢', '哈哈', '测试'}


def grade_input(text):
    """v0.20: 按贡献价值分级
    0 = 闲聊/纯标点
    1 = 基础（普通用户输入）
    2 = 专业（含引用/代码块/结构化）
    3 = 极高（长文档/多引用/规范）
    """
    import re as _re
    t = (text or '').strip()
    if len(t) < 5 or t in CHAT_ONLY:
        return 0
    if all(c in '。，！？,.!? ' for c in t):
        return 0
    # 基础分
    score = 1
    # 任务意图 +1
    TASK_WORDS = ('任务', '帮我', '请帮', '麻烦', '#4', '执行', '查一下', '改一下', '写一个', '做一个')
    if any(w in t for w in TASK_WORDS):
        score += 1
    # 复杂度 +1
    MULTI_WORDS = ('步骤', '首先', '然后', '接着', '最后', '多个', '全部')
    if len(t) > 100 or any(w in t for w in MULTI_WORDS):
        score += 1
    # === v0.20: 专业档判定（>= 2 分） ===
    _has_fileline = bool(_re.search(r'[\w/\.\-]+\.\w+:\d+', t))
    _has_codeblock = '```' in t
    _has_filepath = bool(_re.search(r'(?:^|\s)(?:core|static|docs|scripts|harness_modules|data|logs)/', t))
    _has_numbered = bool(_re.search(r'(?:^|\n)\s*\d+[\.\)]\s', t))
    if _has_fileline or _has_codeblock or _has_filepath or (_has_numbered and len(t) > 100):
        score = max(score, 2)
    # === v0.20: 极高档判定（= 3 分） ===
    _fileline_count = len(_re.findall(r'[\w/\.\-]+\.\w+:\d+', t))
    _has_table = bool(_re.search(r'\|[^\n]+\|', t))
    _has_spec_kw = any(w in t for w in ('规范', '标准', '协议', '设计文档', '架构', '方案'))
    if len(t) > 500 or _fileline_count >= 5 or (_has_spec_kw and len(t) > 300) or _has_table:
        score = 3
    return min(score, 3)


def try_pollinate_from_input(user_id, conversation_id, content):
    text = (content or '').strip()
    for p in ('[TASK]:', '[STEP_DONE]:', '[IMAGE]:', '[FILE]:', '[RED_PACKET]:',
              '[TRANSFER]:', '[SUMMARY]:', '[RETRY_TASK]:', '[TASK_DRAFT]:',
              '[SUPERVISOR_PROGRESS]:'):
        if text.startswith(p):
            return {'reward': 0, 'reason': 'protocol'}
    reward = grade_input(text)
    if reward <= 0:
        return {'reward': 0, 'reason': 'low_value'}
    five_min_ago = (datetime.now() - timedelta(minutes=5)).isoformat()
    with db_cursor() as cur:
        cur.execute("""
            SELECT id FROM contribution_log
            WHERE user_id=? AND event_type='input_pollination'
              AND detail LIKE ? AND created_at > ?
            LIMIT 1
        """, (user_id, f'%conversation_id={conversation_id}%', five_min_ago))
        if cur.fetchone():
            return {'reward': 0, 'reason': 'cooldown'}
    import hashlib
    h = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
    day_ago = (datetime.now() - timedelta(hours=24)).isoformat()
    with db_cursor() as cur:
        cur.execute("""
            SELECT id FROM contribution_log
            WHERE user_id=? AND event_type='input_pollination'
              AND detail LIKE ? AND created_at > ?
            LIMIT 1
        """, (user_id, f'%hash={h}%', day_ago))
        if cur.fetchone():
            return {'reward': 0, 'reason': 'duplicate'}
    today_points = get_today_pollination_points(user_id)
    if today_points + reward > POLLINATION_DAILY_LIMIT:
        reward = max(0, POLLINATION_DAILY_LIMIT - today_points)
        if reward == 0:
            return {'reward': 0, 'reason': 'daily_limit'}
    credit_service.add_credit(
        user_id, reward,
        action='用户输入授粉',
        detail=f'conversation_id={conversation_id} | hash={h} | {text[:60]}',
        event_type='input_pollination'
    )
    return {'reward': reward, 'reason': 'ok'}



def submit_pollination(user_id: int, task_description: str, solution: str, source: str = "manual") -> dict:
    """
    用户提交授粉回流数据。
    流程：
    1. 风险分级检查
    2. 基础价值评估
    3. 写入知识库（示例为打印/返回，正式可扩展）
    4. 发放积分（受每日上限限制）
    """
    # 1. 风险检查
    risk = safety_scan.analyze_risk(solution)
    if risk["level"] == "high":
        return {"accepted": False, "message": risk["message"]}

    # 2. 价值评估（基础价值，后续可接入 LLM 判断）
    value_level = "basic"
    reward = POLLINATION_REWARD_BASIC

    # 3. 简单去重（示例：不真正入库，只返回积分）
    # 4. 发放积分
    today_points = get_today_pollination_points(user_id) + reward
    if today_points > POLLINATION_DAILY_LIMIT:
        actual_reward = max(0, POLLINATION_DAILY_LIMIT - (today_points - reward))
        reward = actual_reward
        if reward <= 0:
            return {"accepted": True, "message": "今日授粉积分已达上限", "reward": 0}

    credit_service.add_credit(user_id, reward, ("自动授粉" if source == "auto" else "授粉回流"), f"任务：{task_description}", "pollination")

    return {"accepted": True, "message": "授粉成功", "reward": reward}


def submit_falsify(user_id: int, result_id: str, evidence: str) -> dict:
    """
    用户提交证伪反馈。
    流程：
    1. 风险检查证据
    2. 模拟验证（实际应沙箱验证）
    3. 标记污染（示例：写入日志）
    4. 发放积分（受每日上限限制）
    """
    # 1. 风险检查
    risk = safety_scan.analyze_risk(evidence)
    if risk["level"] == "high":
        return {"accepted": False, "message": risk["message"]}

    # 2. 写入污染标记
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO contribution_log (user_id, action, event_type, points, detail)
            VALUES (?, ?, 'falsify', ?, ?)
        """, (user_id, "证伪反馈", FALSIFY_REWARD, f"结果ID：{result_id}，证据：{evidence}"))

    # 3. 发放积分
    today_points = get_today_falsify_points(user_id) + FALSIFY_REWARD
    if today_points > FALSIFY_DAILY_LIMIT:
        actual_reward = max(0, FALSIFY_DAILY_LIMIT - (today_points - FALSIFY_REWARD))
        reward = actual_reward
        if reward <= 0:
            return {"accepted": True, "message": "今日证伪积分已达上限", "reward": 0}
    else:
        reward = FALSIFY_REWARD

    credit_service.add_credit(user_id, reward, "挑坏果子", f"结果ID：{result_id}", "falsify")

    return {"accepted": True, "message": "证伪反馈已记录", "reward": reward}
