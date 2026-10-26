# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('users.db')
cur = conn.cursor()
cur.execute("SELECT id FROM messages WHERE conversation_id=25 ORDER BY id DESC LIMIT 5")
ids = [r[0] for r in cur.fetchall()]
print("将删除的消息 ID:", ids)
confirm = input("确认删除？(yes/no): ")
if confirm.lower() == "yes":
    for mid in ids:
        cur.execute("DELETE FROM messages WHERE id=?", (mid,))
    conn.commit()
    print(f"已删除 {len(ids)} 条消息")
else:
    print("已取消")
