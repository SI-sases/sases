import json
from .. import memory_service

def _save_task_state(task_id, user_id, state_dict):
    """保存任务状态到 memory（v0.19）"""
    try:
        from .. import memory_service
        import json as _json
        memory_service.remember(
            user_id=user_id,
            memory_type='task_state',
            content=_json.dumps(state_dict, ensure_ascii=False),
            task_id=task_id,
            importance=0.7,
            tags='snapshot,swarm',
            enable_dedup=False
        )
    except Exception as e:
        print(f'[state] save failed: {e}')


def _load_task_state(task_id, user_id):
    """加载最近一条任务状态（v0.20：直查 DB）"""
    try:
        import json as _json
        from ...db import db_cursor
        with db_cursor() as _c:
            _c.execute(
                "SELECT content FROM safety_memory WHERE task_id=? AND memory_type='task_state' AND user_id=? ORDER BY id DESC LIMIT 1",
                (task_id, user_id)
            )
            _row = _c.fetchone()
        if not _row:
            print(f'[state] load 未命中 {task_id}')
            return None
        _content = _row["content"] if isinstance(_row, dict) else _row[0]
        _parsed = _json.loads(_content or '{}')
        print(f'[state] load 命中 {task_id}, facts={len(_parsed.get("facts", []))}')
        return _parsed
    except Exception as e:
        print(f'[state] load failed: {e}')
        return None

