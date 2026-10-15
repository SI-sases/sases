import os
import shutil
import ast
from datetime import datetime

FP = "core/services/feedback_service.py"
backup_dir = ".backups"
os.makedirs(backup_dir, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
backup = os.path.join(backup_dir, f"core__services__feedback_service.py.{ts}.bak")
shutil.copy2(FP, backup)
print(f"备份: {backup}")

with open(FP, 'r', encoding='utf-8') as f:
    c = f.read()

changes = 0

# ===== 改动 1：submit_explicit 权限校验加回退 =====
old1 = '''    # 权限校验：task 必须属于该用户
    with db_cursor() as cur:
        cur.execute(
            "SELECT user_id, conversation_id FROM swarm_pending_tasks WHERE task_id=?",
            (task_id,)
        )
        row = cur.fetchone()
        if not row:
            return {"ok": False, "message": "任务不存在"}
        if int(row["user_id"]) != int(user_id):
            return {"ok": False, "message": "无权反馈"}
        if conversation_id is None:
            conversation_id = row["conversation_id"]'''

new1 = '''    # 权限校验：task 必须属于该用户
    # 优先 swarm_pending_tasks（任务运行中），任务完成后记录会被删
    # 回退到 swarm_reviews + conversations（任务完成后仍有审核日志）
    with db_cursor() as cur:
        cur.execute(
            "SELECT user_id, conversation_id FROM swarm_pending_tasks WHERE task_id=?",
            (task_id,)
        )
        row = cur.fetchone()
        if not row:
            # 回退 1：从 swarm_reviews 拿 conversation_id
            cur.execute(
                "SELECT conversation_id FROM swarm_reviews WHERE task_id=? LIMIT 1",
                (task_id,)
            )
            rev = cur.fetchone()
            if rev and rev["conversation_id"]:
                _cid = rev["conversation_id"]
                # 从 conversations 拿 user_id
                cur.execute("SELECT user_id FROM conversations WHERE id=?", (_cid,))
                conv = cur.fetchone()
                if conv:
                    row = {"user_id": conv["user_id"], "conversation_id": _cid}
        if not row:
            return {"ok": False, "message": "任务不存在或已过期"}
        if int(row["user_id"]) != int(user_id):
            return {"ok": False, "message": "无权反馈"}
        if conversation_id is None:
            conversation_id = row["conversation_id"]'''

if old1 in c:
    c = c.replace(old1, new1, 1)
    changes += 1
    print("改动 1: submit_explicit 权限校验加回退")
else:
    print("警告：改动 1 锚点未匹配")

# ===== 改动 2：_build_task_snapshot 加回退 =====
old2 = '''def _build_task_snapshot(task_id: str) -> dict:
    """从 swarm_pending_tasks 拉任务快照"""
    with db_cursor() as cur:
        cur.execute(
            "SELECT user_text, steps, supervisor_run_id FROM swarm_pending_tasks WHERE task_id=?",
            (task_id,)
        )
        row = cur.fetchone()
    if not row:
        return {
            "user_input": "",
            "mode": "unknown",
            "steps_total": 0,
            "steps_tools": [],
            "retry_count": 0,
            "has_answer": False,
            "context_hint": "",
        }'''

new2 = '''def _build_task_snapshot(task_id: str) -> dict:
    """从 swarm_pending_tasks 拉任务快照；任务完成后回退到 reviews"""
    with db_cursor() as cur:
        cur.execute(
            "SELECT user_text, steps, supervisor_run_id FROM swarm_pending_tasks WHERE task_id=?",
            (task_id,)
        )
        row = cur.fetchone()
    if not row:
        # 任务已完成：从 supervisor_runs.goal 拉目标
        with db_cursor() as cur:
            cur.execute(
                "SELECT goal FROM supervisor_runs WHERE id=(SELECT supervisor_run_id FROM swarm_reviews WHERE task_id=? LIMIT 1)",
                (task_id,)
            )
            r2 = cur.fetchone()
            _goal = r2["goal"] if r2 and r2["goal"] else ""
        return {
            "user_input": _goal[:2000],
            "mode": "swarm",
            "steps_total": 0,
            "steps_tools": [],
            "retry_count": 0,
            "has_answer": False,
            "context_hint": "",
        }'''

if old2 in c:
    c = c.replace(old2, new2, 1)
    changes += 1
    print("改动 2: _build_task_snapshot 加回退")
else:
    print("警告：改动 2 锚点未匹配")

# ===== 改动 3：_build_result_snapshot 加回退 =====
old3 = '''def _build_result_snapshot(task_id: str) -> dict:
    """从 swarm_pending_tasks.results 拉结果快照"""
    with db_cursor() as cur:
        cur.execute(
            "SELECT results, retry_count, status, created_at FROM swarm_pending_tasks WHERE task_id=?",
            (task_id,)
        )
        row = cur.fetchone()
    if not row:
        return {
            "status": "unknown",
            "duration_ms": 0,
            "steps_done": 0,
            "final_output_len": 0,
            "restart_pending": False,
            "files_touched": [],
        }'''

new3 = '''def _build_result_snapshot(task_id: str) -> dict:
    """从 swarm_pending_tasks.results 拉结果快照；任务完成后回退到 reviews 统计"""
    with db_cursor() as cur:
        cur.execute(
            "SELECT results, retry_count, status, created_at FROM swarm_pending_tasks WHERE task_id=?",
            (task_id,)
        )
        row = cur.fetchone()
    if not row:
        # 任务已完成：从 swarm_reviews 聚合
        with db_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as total, SUM(CASE WHEN exec_status='success' THEN 1 ELSE 0 END) as ok FROM swarm_reviews WHERE task_id=?",
                (task_id,)
            )
            r2 = cur.fetchone()
        _total = r2["total"] if r2 else 0
        _ok = r2["ok"] if r2 and r2["ok"] else 0
        return {
            "status": "completed",
            "duration_ms": 0,
            "steps_done": _ok,
            "steps_total": _total,
            "final_output_len": 0,
            "restart_pending": False,
            "files_touched": [],
        }'''

if old3 in c:
    c = c.replace(old3, new3, 1)
    changes += 1
    print("改动 3: _build_result_snapshot 加回退")
else:
    print("警告：改动 3 锚点未匹配")

print(f"\n共 {changes} 处改动")

try:
    ast.parse(c)
    print("语法检查通过")
except SyntaxError as e:
    print(f"语法失败: {e}")
    shutil.copy2(backup, FP)
    raise SystemExit(1)

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)
print(f"已写入，大小 {os.path.getsize(FP)} 字节")

print("\n完成！下一步：")
print("1. 重启服务：Ctrl+C 后 python scripts/run_forever.py")
print("2. 硬刷新浏览器")
print("3. 发 swarm 任务 → 任务完成后点 👎 → 应显示'已记录'")
print("4. 查数据库：")
print("   python -c \"import sqlite3; c=sqlite3.connect('users.db'); c.row_factory=sqlite3.Row; cur=c.cursor(); cur.execute('SELECT id, task_id, rating, feedback_type FROM task_feedback ORDER BY id DESC LIMIT 3'); [print(dict(r)) for r in cur.fetchall()]\"")
print("5. del fix_feedback_fallback.py")