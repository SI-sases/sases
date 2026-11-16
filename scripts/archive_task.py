# -*- coding: utf-8 -*-
"""归档当前任务：active/CURRENT_TASK.md → archive/日期_任务名/，并清 task_context + 同步数据库。

用法：
  python scripts/archive_task.py --task p2-build --dry-run
  python scripts/archive_task.py --task p2-build
"""
import argparse
import shutil
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
ACTIVE = ROOT / 'docs' / 'tasks' / 'active'
ARCHIVE = ROOT / 'docs' / 'tasks' / 'archive'
DB = ROOT / 'users.db'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--task', required=True)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-sync', action='store_true', help='跳过数据库同步')
    args = ap.parse_args()

    src = ACTIVE / 'CURRENT_TASK.md'
    if not src.exists():
        print('[FATAL] 文件不存在: {}'.format(src))
        sys.exit(1)

    dest_dir = ARCHIVE / '{}_{}'.format(date.today().isoformat(), args.task)
    if dest_dir.exists():
        n = 2
        while (ARCHIVE / '{}_{}_{}'.format(date.today().isoformat(), args.task, n)).exists():
            n += 1
        dest_dir = ARCHIVE / '{}_{}_{}'.format(date.today().isoformat(), args.task, n)

    if args.dry_run:
        print('[dry-run] 将移动: {} → {}'.format(src, dest_dir))
        print('[dry-run] 将清理 task_context 中 task:{}'.format(args.task))
        if not args.no_sync:
            print('[dry-run] 将执行 import_project_docs.py --sync')
        print('[dry-run] 未做任何改动')
        return

    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest_dir / 'CURRENT_TASK.md'))
    print('[archive] 已移动: {} → {}'.format(src, dest_dir))

    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM safety_memory WHERE memory_type='task_context' AND ',' || tags || ',' LIKE ?",
        ('%,task:{},%'.format(args.task),)
    )
    n_ctx = cur.rowcount
    conn.commit()
    conn.close()
    print('[archive] 清理 task_context: {} 条'.format(n_ctx))

    if not args.no_sync:
        print('[archive] 执行 --sync 清理数据库镜像...')
        r = subprocess.run(
            [sys.executable, str(ROOT / 'scripts' / 'import_project_docs.py'), '--sync'],
            capture_output=True, text=True, timeout=60, cwd=str(ROOT)
        )
        if r.stdout:
            print(r.stdout)
        if r.returncode != 0:
            print('[WARN] --sync 返回 {}: {}'.format(r.returncode, r.stderr[:200]))

    # 自检
    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM safety_memory WHERE memory_type='task_context' AND ',' || tags || ',' LIKE ?",
        ('%,task:{},%'.format(args.task),)
    )
    remain_ctx = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM project_docs WHERE source_file LIKE 'task__%'")
    remain_proj = cur.fetchone()[0]
    conn.close()

    print('[verify] task_context 残留: {}'.format(remain_ctx))
    print('[verify] task__ 项目分片残留: {}'.format(remain_proj))
    if remain_ctx > 0 or remain_proj > 0:
        print('[FAIL] 有残留，归档不完整')
        sys.exit(2)
    print('[OK] 归档完成')


if __name__ == '__main__':
    main()
