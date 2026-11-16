#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P0：写 task_context + 清历史遗留。先 dry-run，再 --confirm。"""
import sqlite3, hashlib, sys, argparse
from datetime import datetime, timedelta
from pathlib import Path

# ============ 你只改这 5 个值 ============
TASK_NAME = "p2-build"          # 任务名，英文短横线
WINDOW    = "win-p2-build"      # 窗口名
USER_ID   = 1                   # 你的 user_id
EXPIRE_DAYS = 3                 # 几天后自动过期

TASK_CONTENT = """当前任务：P2 建表。
目标：建 nodes/api_registry/cognitive_rules 等表，不破坏现有功能。
涉及：core/db.py, core/migrations.py, users.db。
验收：PRAGMA table_info(nodes) 有字段；现有功能跑通。
坑点：file_patch 前必 file_read；大段替换固化成 scripts/xxx.py；改 core/ 必须重启；不动 users.db 结构外的东西。
回滚：git checkout <pre-p2>。"""
# =========================================

DB = Path(__file__).parent.parent / "users.db"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--confirm", action="store_true", help="真正执行，不加只 dry-run")
    args = p.parse_args()

    conn = sqlite3.connect(str(DB)); conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    tag = f"task:{TASK_NAME}"
    expires = (datetime.now() + timedelta(days=EXPIRE_DAYS)).isoformat()

    # 1. 看现有 task_context
    cur.execute("SELECT id, tags, expires_at FROM safety_memory WHERE memory_type='task_context' ORDER BY id DESC")
    rows = cur.fetchall()
    print(f"[现状] task_context 共 {len(rows)} 条")
    for r in rows:
        print(f"  id={r['id']}  expires={r['expires_at']}  tags={r['tags']}")

    # 2. 找要删的（tags 不含 task:{TASK_NAME} 的）
    to_delete = [r["id"] for r in rows if tag not in (r["tags"] or "")]
    print(f"\n[计划] 删除历史遗留 {len(to_delete)} 条: {to_delete}")
    print(f"[计划] 写入新记录: {tag}, expires={expires}")

    if not args.confirm:
        print("\n[dry-run] 未做任何改动。确认无误后加 --confirm 重跑。")
        return

    # 3. 删旧
    if to_delete:
        cur.executemany("DELETE FROM safety_memory WHERE id=?", [(i,) for i in to_delete])
        print(f"[执行] 删除 {cur.rowcount} 条")

    # 4. 先删同 tag 的旧记录（防重复），再插入
    cur.execute("DELETE FROM safety_memory WHERE memory_type='task_context' AND tags LIKE ?", (f"%,{tag},%",))
    h = hashlib.sha256(TASK_CONTENT.encode()).hexdigest()
    cur.execute("""INSERT INTO safety_memory
        (memory_type, content, user_id, importance, tags, expires_at, content_hash, created_at)
        VALUES (?,?,?,?,?,?,?,?)""",
        ("task_context", TASK_CONTENT, USER_ID, 0.95,
         f"task_context,current,{tag},window:{WINDOW}",
         expires, h, datetime.now().isoformat()))
    conn.commit()

    # 5. 验证
    print("\n[验证] 最终状态：")
    cur.execute("SELECT id, tags, expires_at FROM safety_memory WHERE memory_type='task_context'")
    for r in cur.fetchall():
        print(f"  id={r['id']}  expires={r['expires_at']}  tags={r['tags']}")
    print("[OK] P0 完成")

if __name__ == "__main__":
    main()
