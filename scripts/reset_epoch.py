"""reset_epoch.py —— 清所有节点的 master_epoch 为 0。

注意：需要先停止所有节点。
"""
import sqlite3
import os

DBS = [
    'users.db',
    'hive-nodes/node-B/replica.db',
    'hive-nodes/node-C/replica.db',
]

for p in DBS:
    if not os.path.exists(p):
        print(f'{p}: 不存在，跳过')
        continue
    try:
        conn = sqlite3.connect(p)
        cur = conn.cursor()
        cur.execute('UPDATE node_registry SET master_epoch=0')
        conn.commit()
        n = cur.rowcount
        conn.close()
        print(f'{p}: 清 {n} 行')
    except Exception as e:
        print(f'{p}: 失败 {e}')

print()
print('=== 验证 ===')
for p in DBS:
    if not os.path.exists(p):
        continue
    conn = sqlite3.connect(p)
    cur = conn.cursor()
    cur.execute('SELECT node_id, master_epoch FROM node_registry WHERE master_epoch > 0')
    rows = cur.fetchall()
    conn.close()
    print(f'{p}: {rows if rows else "全部为0"}')