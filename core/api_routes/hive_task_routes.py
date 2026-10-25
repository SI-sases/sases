"""蜂群任务跨实例同步路由"""
from fastapi import APIRouter
from ..db import db_cursor

router = APIRouter(prefix="/hive", tags=["hive-task"])


@router.post("/sync/task")
def sync_task(body: dict):
    """接收 peer 的群任务发布通知"""
    _ggid = body.get('global_group_id')
    _gtid = body.get('global_task_id')
    if not _ggid or not _gtid:
        return {'ok': False, 'error': 'missing params'}
    with db_cursor() as cur:
        cur.execute("SELECT id FROM groups WHERE global_group_id=?", (_ggid,))
        g = cur.fetchone()
        if not g:
            return {'ok': False, 'error': 'group not found'}
        cur.execute("SELECT id FROM group_tasks WHERE global_task_id=?", (_gtid,))
        if cur.fetchone():
            return {'ok': True, 'skipped': True}
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO group_tasks (group_id, global_task_id, title, description, task_category, created_by, reward_credits, status, origin_node) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (g['id'], _gtid, body.get('title', ''), body.get('description', ''), body.get('task_category', 'text'), 1, body.get('reward_credits', 0), 'open', body.get('origin_node'))
            )
        return {'ok': True, 'created': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


@router.post("/sync/submission")
def sync_submission(body: dict):
    """接收 peer 的方案提交同步"""
    _ggid = body.get('global_group_id')
    _gtid = body.get('global_task_id')
    _gsid = body.get('global_submission_id')
    if not _ggid or not _gtid or not _gsid:
        return {'ok': False, 'error': 'missing params'}
    with db_cursor() as cur:
        cur.execute("SELECT id FROM groups WHERE global_group_id=?", (_ggid,))
        g = cur.fetchone()
        if not g:
            return {'ok': False, 'error': 'group not found'}
        cur.execute("SELECT id FROM group_tasks WHERE global_task_id=?", (_gtid,))
        t = cur.fetchone()
        if not t:
            return {'ok': False, 'error': 'task not found'}
        cur.execute("SELECT id FROM group_task_submissions WHERE global_submission_id=?", (_gsid,))
        if cur.fetchone():
            return {'ok': True, 'skipped': True}
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO group_task_submissions (task_id, global_submission_id, submitted_by, content, content_type) VALUES (?, ?, ?, ?, ?)",
                (t['id'], _gsid, 1, body.get('content', ''), body.get('content_type', 'text'))
            )
        return {'ok': True, 'created': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


@router.post("/sync/task-result")
def sync_task_result(body: dict):
    """接收 peer 的任务结果同步"""
    _ggid = body.get('global_group_id')
    _gtid = body.get('global_task_id')
    if not _ggid or not _gtid:
        return {'ok': False, 'error': 'missing params'}
    with db_cursor() as cur:
        cur.execute("SELECT id FROM groups WHERE global_group_id=?", (_ggid,))
        g = cur.fetchone()
        if not g:
            return {'ok': False, 'error': 'group not found'}
        cur.execute("SELECT id FROM group_tasks WHERE global_task_id=?", (_gtid,))
        t = cur.fetchone()
        if not t:
            return {'ok': False, 'error': 'task not found'}
    try:
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE group_tasks SET status='done' WHERE id=?", (t['id'],))
        return {'ok': True, 'updated': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
