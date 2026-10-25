# core/services/cleanup_service.py
"""
SASES 数据清理服务
- safety_memory 过期清理
- swarm_reviews 保留 30 天
- swarm_pending_tasks 完成/取消/无计划 保留 7 天
"""
import asyncio
from datetime import datetime, timedelta
from ..db import db_cursor


def cleanup_expired_memory() -> int:
    """删除 expires_at 已过期的记忆"""
    now = datetime.now().isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM safety_memory WHERE expires_at IS NOT NULL AND expires_at < ?",
            (now,)
        )
        return cur.rowcount


def cleanup_old_reviews(days: int = 30) -> int:
    """删除 30 天前的审核日志"""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM swarm_reviews WHERE created_at < ?", (cutoff,))
        return cur.rowcount


def cleanup_finished_swarm_tasks(days: int = 7) -> int:
    """删除 7 天前已完成/取消/无计划的蜂群任务"""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            DELETE FROM swarm_pending_tasks
            WHERE status IN ('completed', 'cancelled', 'no_plan')
              AND updated_at < ?
            """,
            (cutoff,)
        )
        return cur.rowcount


def cleanup_orphan_uploads(days: int = 30, dry_run: bool = True) -> dict:
    """清理 uploads/ 下 30 天前无引用的图片/文件"""
    import os
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'uploads')
    if not os.path.isdir(uploads_dir):
        return {'scanned': 0, 'orphans': 0, 'deleted': 0, 'freed_bytes': 0}
    cutoff = (datetime.now() - timedelta(days=days)).timestamp()
    with db_cursor() as cur:
        cur.execute('SELECT stored_path FROM attachments')
        all_files = set(r['stored_path'] for r in cur.fetchall())
        cur.execute("SELECT content FROM messages WHERE content LIKE '%/uploads/%'")
        referenced = set()
        for r in cur.fetchall():
            content = r['content'] or ''
            for fn in all_files:
                if fn in content:
                    referenced.add(fn)
    scanned = 0
    orphans = 0
    deleted = 0
    freed = 0
    for fn in os.listdir(uploads_dir):
        fp = os.path.join(uploads_dir, fn)
        if not os.path.isfile(fp):
            continue
        scanned += 1
        try:
            mtime = os.path.getmtime(fp)
            size = os.path.getsize(fp)
        except Exception:
            continue
        if fn in referenced:
            continue
        if mtime >= cutoff:
            continue
        orphans += 1
        if not dry_run:
            try:
                os.remove(fp)
                deleted += 1
                freed += size
            except Exception as e:
                print('[cleanup] 删除失败 ' + fn + ': ' + str(e))
    return {'scanned': scanned, 'orphans': orphans, 'deleted': deleted, 'freed_bytes': freed}


def cleanup_low_value_memory(min_importance: float = 0.3, min_days: int = 60) -> int:
    """删除低价值且较老的记忆"""
    cutoff = (datetime.now() - timedelta(days=min_days)).isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM safety_memory WHERE importance < ? AND created_at < ? AND memory_type != 'task_result'",
            (min_importance, cutoff)
        )
        return cur.rowcount



def cleanup_protocol_messages(days: int = 30) -> int:
    """删除 N 天前的协议消息（TASK/STEP_DONE/SUMMARY 等）"""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    prefixes = ('[TASK]:', '[STEP_DONE]:', '[TASK_DRAFT]:', '[RETRY_TASK]:', '[SUMMARY]:')
    with db_cursor(commit=True) as cur:
        conds = ' OR '.join(['content LIKE ?' for _ in prefixes])
        params = [p + '%' for p in prefixes]
        params.append(cutoff)
        cur.execute('DELETE FROM messages WHERE (' + conds + ') AND created_at < ?', params)
        return cur.rowcount


def cleanup_old_execution_notes(days: int = 180) -> int:
    """删除 N 天前、outcome 非 important 的执行笔记"""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM execution_notes WHERE created_at < ? AND (outcome IS NULL OR outcome != 'important')", (cutoff,))
        return cur.rowcount


def cleanup_low_value_patterns() -> dict:
    """清理低价值 pattern：tentative 超 30 天删，active 低命中超 90 天归档"""
    now = datetime.now()
    t30 = (now - timedelta(days=30)).isoformat()
    t90 = (now - timedelta(days=90)).isoformat()
    deleted = 0
    archived = 0
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM interaction_patterns WHERE status='tentative' AND created_at < ?", (t30,))
        deleted = cur.rowcount
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE interaction_patterns SET status='archived' WHERE status='active' AND hit_count <= 5 AND created_at < ? AND (last_hit_at IS NULL OR last_hit_at < ?)", (t90, t90))
        archived = cur.rowcount
    return {'deleted': deleted, 'archived': archived}



def scan_test_marks(dry_run: bool = True) -> dict:
    """扫描代码里的测试残留标记。dry_run=True 只报告不删除。"""
    import os as _os
    PATTERNS = ['e2e-restart-test', 'restart-cycle-test', 'file_patch 权限测试', '# TEST:']
    SCAN_DIRS = ['core', 'static', 'scripts', 'harness_modules']
    findings = []
    for _d in SCAN_DIRS:
        if not _os.path.isdir(_d):
            continue
        for _root, _, _files in _os.walk(_d):
            if 'venv' in _root or '.git' in _root or '__pycache__' in _root or '.backups' in _root:
                continue
            for _f in _files:
                if not _f.endswith(('.py', '.js', '.css', '.html')):
                    continue
                if _f == 'cleanup_service.py':
                    continue
                _fp = _os.path.join(_root, _f)
                try:
                    with open(_fp, 'r', encoding='utf-8', errors='ignore') as _fh:
                        for _i, _line in enumerate(_fh, 1):
                            for _p in PATTERNS:
                                if _p in _line:
                                    findings.append({'file': _fp, 'line': _i, 'text': _line.strip()[:120]})
                except Exception:
                    pass
    return {'dry_run': dry_run, 'count': len(findings), 'findings': findings}


def cleanup_stale_task_state(keep_per_task: int = 1, days: int = 7) -> int:
    """清理 task_state 类型记忆：每个 task_id 只保留最新 N 条，并删除超 N 天的记录"""
    deleted = 0
    try:
        with db_cursor(commit=True) as cur:
            cur.execute("""
                DELETE FROM safety_memory
                WHERE memory_type='task_state'
                  AND id IN (
                    SELECT s1.id FROM safety_memory s1
                    WHERE s1.memory_type='task_state'
                      AND (SELECT COUNT(*) FROM safety_memory s2
                           WHERE s2.memory_type='task_state'
                             AND s2.task_id = s1.task_id
                             AND s2.id > s1.id) >= ?
                  )
            """, (keep_per_task,))
            deleted += cur.rowcount
            cur.execute("""
                DELETE FROM safety_memory
                WHERE memory_type='task_state'
                  AND created_at < datetime('now', ?)
            """, (f'-{days} days',))
            deleted += cur.rowcount
    except Exception as e:
        print(f'[cleanup] stale_task_state 失败: {e}')
    return deleted



def cleanup_stale_task_state(keep_per_task: int = 1, days: int = 7) -> int:
    """清理 task_state 类型记忆：
    1) 每个 task_id 只保留最新 N 条
    2) 超过 N 天的全部删除
    """
    deleted = 0
    try:
        with db_cursor(commit=True) as cur:
            cur.execute("""
                DELETE FROM safety_memory
                WHERE memory_type='task_state'
                  AND id IN (
                    SELECT s1.id FROM safety_memory s1
                    WHERE s1.memory_type='task_state'
                      AND (SELECT COUNT(*) FROM safety_memory s2
                           WHERE s2.memory_type='task_state'
                             AND s2.task_id = s1.task_id
                             AND s2.id > s1.id) >= ?
                  )
            """, (keep_per_task,))
            deleted += cur.rowcount
            cur.execute("""
                DELETE FROM safety_memory
                WHERE memory_type='task_state'
                  AND created_at < datetime('now', ?)
            """, (f'-{days} days',))
            deleted += cur.rowcount
    except Exception as e:
        print(f'[cleanup] stale_task_state 失败: {e}')
    return deleted



def cleanup_all() -> dict:
    """执行全部清理任务，返回各项删除数量"""
    result = {
        "expired_memory": 0,
        "old_reviews": 0,
        "finished_swarm_tasks": 0,
        "orphan_uploads": 0,
        "low_value_memory": 0,
        "protocol_messages": 0,
        "old_execution_notes": 0,
        "patterns_deleted": 0,
        "patterns_archived": 0,
        "test_marks_found": 0,
        "test_marks_detail": [],
        "test_marks_found": 0,
        "test_marks_detail": [],
    }
    try:
        result["expired_memory"] = cleanup_expired_memory()
    except Exception as e:
        print(f"[cleanup] 过期记忆清理失败: {e}")

    try:
        result["old_reviews"] = cleanup_old_reviews(days=30)
    except Exception as e:
        print(f"[cleanup] 审核日志清理失败: {e}")

    try:
        result["finished_swarm_tasks"] = cleanup_finished_swarm_tasks(days=7)
    except Exception as e:
        print(f"[cleanup] 蜂群任务清理失败: {e}")

    try:
        _up = cleanup_orphan_uploads(days=30, dry_run=True)
        result['orphan_uploads'] = _up['orphans']
        print('[cleanup] uploads 扫描: ' + str(_up))
    except Exception as e:
        print('[cleanup] uploads 清理失败: ' + str(e))

    try:
        result['low_value_memory'] = cleanup_low_value_memory()
    except Exception as e:
        print('[cleanup] 低价值记忆清理失败: ' + str(e))


    try:
        result['protocol_messages'] = cleanup_protocol_messages(days=30)
    except Exception as e:
        print('[cleanup] 协议消息清理失败: ' + str(e))

    try:
        result['old_execution_notes'] = cleanup_old_execution_notes(days=180)
    except Exception as e:
        print('[cleanup] 执行笔记清理失败: ' + str(e))

    try:
        _p = cleanup_low_value_patterns()
        result['patterns_deleted'] = _p['deleted']
        result['patterns_archived'] = _p['archived']
    except Exception as e:
        print('[cleanup] pattern 清理失败: ' + str(e))

    try:
        result['stale_task_state'] = cleanup_stale_task_state(keep_per_task=1, days=7)
    except Exception as e:
        print('[cleanup] task_state 清理失败: ' + str(e))

    try:
        _tm = scan_test_marks(dry_run=True)
        result['test_marks_found'] = _tm['count']
        result['test_marks_detail'] = _tm['findings'][:10]
        if _tm['count'] > 0:
            print('[cleanup] 测试标记扫描: 发现 ' + str(_tm['count']) + ' 处')
            for _item in _tm['findings'][:10]:
                print('  - ' + _item['file'] + ':' + str(_item['line']) + ': ' + _item['text'])
    except Exception as e:
        print('[cleanup] 测试标记扫描失败: ' + str(e))
    try:
        _tm = scan_test_marks(dry_run=True)
        result['test_marks_found'] = _tm['count']
        result['test_marks_detail'] = _tm.get('findings', [])
    except Exception as e:
        print('[cleanup] 测试标记扫描失败: ' + str(e))

    print(f"[cleanup] 清理完成: {result}")
    return result


async def periodic_cleanup(interval_hours: int = 24):
    """后台定时任务：每 24 小时执行一次清理"""
    # 启动时等 5 分钟再执行，避免和启动备份/其他任务抢资源
    await asyncio.sleep(5 * 60)
    while True:
        try:
            await asyncio.to_thread(cleanup_all)
        except Exception as e:
            print(f"[cleanup] 周期任务异常: {e}")
        await asyncio.sleep(interval_hours * 3600)
