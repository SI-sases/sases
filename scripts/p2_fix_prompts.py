# -*- coding: utf-8 -*-
"""修 _load_task_state：直接按 task_id 查 DB，不走 recall_by_type 全表扫描"""
F = "core/services/swarm/task_state.py"
c = open(F, encoding="utf-8").read()

OLD = '''def _load_task_state(task_id, user_id):
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
        return None'''

NEW = '''def _load_task_state(task_id, user_id):
    """加载最近一条任务状态（v0.20：直查 DB，避免全表扫描）"""
    try:
        import json as _json
        from ...db import db_cursor
        with db_cursor() as _c:
            _c.execute(
                "SELECT content FROM safety_memory "
                "WHERE task_id=? AND memory_type='task_state' AND user_id=? "
                "ORDER BY id DESC LIMIT 1",
                (task_id, user_id)
            )
            _row = _c.fetchone()
        if not _row:
            print(f'[state] load 未命中 {task_id}')
            return None
        _content = _row['content'] if isinstance(_row, dict) else _row[0]
        _parsed = _json.loads(_content or '{}')
        print(f'[state] load 命中 {task_id}, facts={len(_parsed.get("facts", []))}')
        return _parsed
    except Exception as e:
        print(f'[state] load failed: {e}')
        return None'''

if OLD not in c:
    print("[ERR] 锚点未找到，task_state.py 可能已改过")
    # 打印当前 _load_task_state 函数
    i = c.find("def _load_task_state")
    if i >= 0:
        print(c[i:i+1200])
else:
    c2 = c.replace(OLD, NEW, 1)
    open(F, "w", encoding="utf-8").write(c2)
    print("[OK] _load_task_state 已改为直查 DB")
    import ast
    ast.parse(c2)
    print("[OK] 语法通过")
