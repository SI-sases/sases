# scripts/restore_user_api_from_backup.py
import sqlite3
import json
import os

SRC = "backups/users_20261110.db"
DST = "users.db"
TABLE = "user_api_configs"

def main():
    if not os.path.exists(SRC):
        print("ERROR: source not found: " + SRC)
        return

    # 1. 从源库导出建表语句
    src = sqlite3.connect(SRC)
    src.row_factory = sqlite3.Row
    cur = src.cursor()
    cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE,)
    )
    row = cur.fetchone()
    if not row:
        print("ERROR: table not found in source")
        return
    create_sql = row[0]
    print("=== 原始建表语句 ===")
    print(create_sql)
    print()

    # 2. 从源库导出数据
    cur.execute("SELECT * FROM " + TABLE)
    rows = [dict(r) for r in cur.fetchall()]
    print("=== 数据行数: " + str(len(rows)) + " ===")
    for r in rows:
        # 敏感字段脱敏显示
        show = dict(r)
        if show.get("auth_key_encrypted"):
            show["auth_key_encrypted"] = "***(" + str(len(show["auth_key_encrypted"])) + " chars)***"
        print(json.dumps(show, ensure_ascii=False))
    print()
    src.close()

    # 3. 在目标库建表
    dst = sqlite3.connect(DST)
    dst_cur = dst.cursor()
    dst_cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE,)
    )
    if dst_cur.fetchone():
        print("目标库已有 " + TABLE + " 表，不重复建")
        dst.close()
        return

    dst_cur.execute(create_sql)
    print("已在 " + DST + " 建表")

    # 4. 插入数据
    if rows:
        cols = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)
        insert_sql = "INSERT INTO " + TABLE + " (" + col_names + ") VALUES (" + placeholders + ")"
        for r in rows:
            dst_cur.execute(insert_sql, [r[c] for c in cols])
        dst.commit()
        print("已插入 " + str(len(rows)) + " 行数据")

    # 5. 验证
    dst_cur.execute("SELECT COUNT(*) FROM " + TABLE)
    cnt = dst_cur.fetchone()[0]
    dst_cur.execute("PRAGMA table_info(" + TABLE + ")")
    cols = [r[1] for r in dst_cur.fetchall()]
    print()
    print("=== 目标库验证 ===")
    print("行数: " + str(cnt))
    print("字段: " + ", ".join(cols))
    dst.close()

if __name__ == "__main__":
    main()