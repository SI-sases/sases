# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('users.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("""
    SELECT id, sender, sender_agent_id, substr(content, 1, 200) as c
    FROM messages
    WHERE conversation_id=25
    ORDER BY id DESC
    LIMIT 10
""")
for r in cur.fetchall():
    print(f"#{r['id']} | {r['sender']} | {r['sender_agent_id']} | {r['c']}")
    print("-" * 60)
