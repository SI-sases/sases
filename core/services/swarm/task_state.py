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
    """加载最近一条任务状态（v0.19）"""
    try:
        from .. import memory_service
        import json as _json
        rows = memory_service.recall_by_type(user_id, 'task_state', top_k=20)
        print(f'[state] load 查询 task_id={task_id}, 返回 {len(rows)} 条')
        for r in (rows or []):
            _rid = r.get('task_id')
            if _rid == task_id:
                try:
                    _parsed = _json.loads(r.get('content') or '{}')
                    print(f'[state] load 命中 {task_id}, facts={len(_parsed.get("facts", []))}')
                    return _parsed
                except Exception as _je:
                    print(f'[state] load json failed: {_je}')
                    return None
        print(f'[state] load 未命中 {task_id}，现有: ' + str([r.get('task_id') for r in (rows or [])]))
        return None
    except Exception as e:
        print(f'[state] load failed: {e}')
        return None
