import json
from typing import Dict, Any, Optional
from datetime import datetime
from ...db import db_cursor
from .memory_cache import _pending, _feedback_table_ready, _review_table_ready
import core.services.swarm.memory_cache as _mc

def clear_conversation_lock(conversation_id: str) -> bool:
    cleared = False
    for task_id in list(_pending.keys()):
        task = _pending.get(task_id) or {}
        if task.get("conversation_id") == conversation_id and task.get("status") in ("pending", "running"):
            task["status"] = "cancelled"
            del _pending[task_id]
            cleared = True
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE swarm_pending_tasks SET status='cancelled' WHERE conversation_id=? AND status IN ('pending','running')",
            (conversation_id,),
        )
        if cur.rowcount:
            cleared = True
        cur.execute(
            "UPDATE supervisor_runs SET status='failed' WHERE conversation_id=? AND status IN ('running','running_resumed','restart_pending')",
            (conversation_id,),
        )
        if cur.rowcount:
            cleared = True
        conn.commit()
        conn.close()
    except Exception:
        pass
    return cleared



def _save_pending(task: Dict[str, Any]):
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO swarm_pending_tasks
                (task_id, conversation_id, user_id, commander_id, executor_id,
                 user_text, steps, results, done_steps, retry_count,
                 is_draft, cancelled, no_plan, status, created_at, updated_at, supervisor_id, supervisor_run_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    conversation_id=excluded.conversation_id,
                    user_id=excluded.user_id,
                    commander_id=excluded.commander_id,
                    executor_id=excluded.executor_id,
                    user_text=excluded.user_text,
                    steps=excluded.steps,
                    results=excluded.results,
                    done_steps=excluded.done_steps,
                    retry_count=excluded.retry_count,
                    is_draft=excluded.is_draft,
                    cancelled=excluded.cancelled,
                    no_plan=excluded.no_plan,
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    supervisor_id=excluded.supervisor_id,
                    supervisor_run_id=excluded.supervisor_run_id
                """,
                (
                    task["task_id"],
                    task.get("conversation_id"),
                    task["user_id"],
                    task.get("commander_id"),
                    task.get("executor_id"),
                    task.get("user_text", ""),
                    json.dumps(task.get("steps", []), ensure_ascii=False),
                    json.dumps(task.get("results", []), ensure_ascii=False),
                    json.dumps(sorted(list(task.get("done", set()))), ensure_ascii=False),
                    task.get("retry_count", 0),
                    1 if task.get("is_draft") else 0,
                    1 if task.get("cancelled") else 0,
                    1 if task.get("no_plan") else 0,
                    _derive_status(task),
                    task.get("created_at", datetime.now().isoformat()),
                    datetime.now().isoformat(),
                    task.get("supervisor_id"),
                    task.get("supervisor_run_id"),
                )
            )
    except Exception as e:
        print(f"[swarm] DB 写入失败: {e}")
        import traceback
        traceback.print_exc()


def _derive_status(task: Dict[str, Any]) -> str:
    if task.get("cancelled"):
        return "cancelled"
    if task.get("no_plan"):
        return "no_plan"
    if task.get("is_draft"):
        return "draft"
    if len(task.get("done", set())) >= len(task.get("steps", [])):
        return "completed"
    if len(task.get("done", set())) > 0:
        return "running"
    return "pending"


def _has_active_task_in_conversation(conversation_id: int) -> bool:
    if not conversation_id:
        return False

    for task in _pending.values():
        if task.get("conversation_id") != conversation_id:
            continue
        if task.get("cancelled") or task.get("no_plan") or task.get("is_draft"):
            continue
        done = task.get("done", set())
        steps = task.get("steps", [])
        if len(done) >= len(steps):
            continue
        return True

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) as cnt FROM swarm_pending_tasks
                WHERE conversation_id=? AND status IN ('pending', 'running')
                """,
                (conversation_id,)
            )
            row = cur.fetchone()
            return bool(row and row["cnt"] > 0)
    except Exception as e:
        print(f"[swarm] 检查活跃任务失败: {e}")
        return False


def _delete_pending_from_db(task_id: str):
    try:
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM swarm_pending_tasks WHERE task_id=?", (task_id,))
    except Exception as e:
        print(f"[swarm] DB 删除失败: {e}")
        import traceback
        traceback.print_exc()


def _load_pending(task_id: str) -> Optional[Dict[str, Any]]:
    try:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM swarm_pending_tasks WHERE task_id=?", (task_id,))
            row = cur.fetchone()
        if not row:
            return None
        row = dict(row)
        return {
            "task_id": row["task_id"],
            "conversation_id": row["conversation_id"],
            "user_id": row["user_id"],
            "commander_id": row["commander_id"],
            "executor_id": row["executor_id"],
            "user_text": row["user_text"] or "",
            "steps": json.loads(row["steps"] or "[]"),
            "results": json.loads(row["results"] or "[]"),
            "done": set(json.loads(row["done_steps"] or "[]")),
            "retry_count": row["retry_count"] or 0,
            "is_draft": bool(row["is_draft"]),
            "cancelled": bool(row["cancelled"]),
            "no_plan": bool(row["no_plan"]),
            "created_at": row["created_at"],
            "supervisor_id": row["supervisor_id"] if "supervisor_id" in row.keys() else None,
            "supervisor_run_id": row["supervisor_run_id"] if "supervisor_run_id" in row.keys() else None,
        }
    except Exception as e:
        print(f"[swarm] DB 加载失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def restore_pending_tasks():
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT task_id FROM swarm_pending_tasks WHERE status IN ('pending', 'running', 'draft')"
            )
            rows = cur.fetchall()
        count = 0
        for row in rows:
            task = _load_pending(row["task_id"])
            if task:
                _pending[task["task_id"]] = task
                count += 1
        print(f"[swarm] 已恢复 {count} 个待处理任务")
        return count
    except Exception as e:
        print(f"[swarm] 恢复任务失败: {e}")
        return 0

def _ensure_feedback_table():
    global _feedback_table_ready
    if _feedback_table_ready:
        return
    with db_cursor(commit=True) as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS intent_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task_id TEXT,
                original_input TEXT NOT NULL,
                feedback_type TEXT NOT NULL DEFAULT 'false_positive',
                note TEXT,
                created_at TEXT NOT NULL
            )
        """)
    _feedback_table_ready = True


def _ensure_review_table():
    global _review_table_ready
    if _review_table_ready:
        return
    with db_cursor(commit=True) as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS swarm_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                conversation_id INTEGER,
                step_id INTEGER,
                command TEXT,
                exec_status TEXT,
                review_result TEXT,
                review_reason TEXT,
                output_preview TEXT,
                created_at TEXT NOT NULL
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_swarm_reviews_task ON swarm_reviews(task_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_swarm_reviews_time ON swarm_reviews(created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_swarm_reviews_conversation ON swarm_reviews(conversation_id)")
    _review_table_ready = True


def _log_review(task_id, conversation_id, step_id, command, exec_status,
                review_result, review_reason, output, step_type=None):
    _ensure_review_table()
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO swarm_reviews
            (task_id, conversation_id, step_id, command, exec_status, review_result, review_reason, output_preview, step_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id, conversation_id, step_id,
                (command or "")[:500], exec_status,
                review_result, review_reason,
                (output or "")[:200], step_type, datetime.now().isoformat()
            )
        )
