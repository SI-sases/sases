"""SASES 状态文档同步服务
- sync_state_doc: 把 docs/SASES_STATE.md 投喂到项目库（user_id=0）
- periodic_state_sync: 每 24 小时执行一次同步
"""
import asyncio
import os


def sync_state_doc() -> dict:
    fp = 'docs/SASES_STATE.md'
    if not os.path.exists(fp):
        return {'ok': False, 'chunks': 0, 'error': 'file not found'}
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            raw = f.read()
    except Exception as e:
        return {'ok': False, 'chunks': 0, 'error': 'read failed: ' + str(e)}
    if not raw:
        return {'ok': False, 'chunks': 0, 'error': 'empty file'}
    try:
        import sqlite3
        from .. import config
        from . import project_service
        try:
            _conn = sqlite3.connect(config.DB_FILE)
            _cur = _conn.cursor()
            _cur.execute("DELETE FROM project_docs WHERE source_file='SASES_STATE.md'")
            _cur.execute("DELETE FROM project_docs_meta WHERE source_file='SASES_STATE.md'")
            _conn.commit()
            _conn.close()
        except Exception as _e_del:
            print(f"[state] 删除旧分片失败: {_e_del}")
        n = project_service.import_document(
            source_file='SASES_STATE.md',
            source_version='v_auto',
            raw_text=raw,
            auto_replace=True,
            user_id=0,
            allow_system=True,
        )
        return {'ok': True, 'chunks': n, 'error': ''}
    except Exception as e:
        return {'ok': False, 'chunks': 0, 'error': 'import failed: ' + str(e)}


def append_recent_fixes_to_doc(max_count: int = 3, days: int = 7) -> int:
    """扫描最近完成的 run，把目标追加到 docs/SASES_STATE.md 的"七、最近修复"章节"""
    import sqlite3
    from datetime import datetime, timedelta
    from .. import config

    fp = 'docs/SASES_STATE.md'
    if not os.path.exists(fp):
        return 0
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception:
        return 0

    start = -1
    end = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('## 七、最近修复'):
            start = i
        elif start != -1 and line.strip().startswith('## ') and i > start:
            end = i
            break
    if start == -1:
        return 0
    if end == -1:
        end = len(lines)

    section_lines = lines[start + 1:end]
    section_text = ''.join(section_lines)

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    try:
        conn = sqlite3.connect(config.DB_FILE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT id, goal, finished_at FROM supervisor_runs WHERE status='completed' AND finished_at > ? ORDER BY id DESC LIMIT ?",
            (cutoff, max_count * 5)
        )
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"[state] 查询 runs 失败: {e}")
        return 0

    added = 0
    for r in rows[:max_count]:
        goal = (r['goal'] or '').strip()[:80]
        if not goal or len(goal) < 8:
            continue
        if goal in section_text:
            continue
        date_str = (r['finished_at'] or '')[:10]
        new_line = f"- {date_str}: {goal}\n"
        insert_at = len(section_lines)
        for i in range(len(section_lines) - 1, -1, -1):
            if section_lines[i].strip() and not section_lines[i].strip().startswith('---'):
                insert_at = i + 1
                break
        section_lines.insert(insert_at, new_line)
        added += 1
        section_text += new_line

    # v0.36.0: 保留最近 30 条，删除更旧的
    _MAX_ENTRIES = 30
    _dash_indices = [i for i, ln in enumerate(section_lines) if ln.strip().startswith('- ')]
    if len(_dash_indices) > _MAX_ENTRIES:
        # 删除最早的（数组前面的），保留最后 30 条
        _to_remove = _dash_indices[:-_MAX_ENTRIES]
        for _i in reversed(_to_remove):
            del section_lines[_i]
        print(f"[state] 清理旧条目 {len(_to_remove)} 条，保留最近 {_MAX_ENTRIES} 条")

    if added > 0:
        new_lines = lines[:start + 1] + section_lines + lines[end:]
        try:
            with open(fp, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
        except Exception as e:
            print(f"[state] 写文档失败: {e}")
            return 0

    return added


async def periodic_state_sync(interval_hours: int = 24):
    import os as _os
    _debug = (_os.environ.get("DEBUG", "").lower() == "true")
    await asyncio.sleep(5 * 60)
    while True:
        try:
            added = await asyncio.to_thread(append_recent_fixes_to_doc, 3, 7)
            if added > 0 and _debug:
                print(f"[state] 追加 {added} 条最近修复到文档")
            r = await asyncio.to_thread(sync_state_doc)
            if r.get('ok'):
                if _debug:
                    print(f"[state] SASES_STATE.md 同步 {r['chunks']} 个分片")
            else:
                if _debug:
                    print(f"[state] 同步失败: {r.get('error')}")
        except FileNotFoundError:
            if _debug:
                print("[state] 状态文件不存在，静默跳过")
        except Exception as e:
            if _debug:
                print(f"[state] 周期任务异常: {e}")
        await asyncio.sleep(interval_hours * 3600)
