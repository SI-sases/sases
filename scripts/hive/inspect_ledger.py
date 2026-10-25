"""inspect_ledger.py —— 查看官方账本最近变化。

用法：
    python scripts/hive/inspect_ledger.py
"""
import sqlite3
import sys

DB = 'users.db'
TABLES = [
    ('contribution_log', 'id, user_id, event_type, points, detail, created_at'),
    ('group_messages',   'id, group_id, sender_id, substr(content,1,60) AS content, created_at'),
    ('groups',           'id, name, owner_id, created_at'),
    ('transactions',     'id, sender_id, receiver_id, amount, tx_type, status, created_at'),
]


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    for table, cols in TABLES:
        print('=' * 60)
        print(f'=== {table} 最近 5 条 ===')
        try:
            cur.execute(f'SELECT {cols} FROM {table} ORDER BY id DESC LIMIT 5')
            rows = cur.fetchall()
            if not rows:
                print('  (空)')
            for r in rows:
                print('  ', r)
            cur.execute(f'SELECT COUNT(*) FROM {table}')
            print(f'  总数: {cur.fetchone()[0]}')
        except Exception as e:
            print(f'  读取失败: {e}')
        print()
    conn.close()


if __name__ == '__main__':
    main()
