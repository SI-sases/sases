"""check_masters.py —— 检查 8002/8003 主节点的当前状态。

用法：
    python scripts/hive/check_masters.py
"""
import os
import sqlite3
import subprocess
import sys


PORTS = [8001, 8002, 8003]
DB_CANDIDATES = [
    ('8001 主库', 'users.db'),
    ('8002 候选', 'D:/sases1/users.db'),
    ('8002 候选(备选)', 'D:/sases/8002/users.db'),
    ('8003 候选', 'D:/sases2/users.db'),
    ('8003 候选(备选)', 'D:/sases/8003/users.db'),
]


def check_db(label, path):
    if not os.path.exists(path):
        print(f'[DB] {label}: {path} → 不存在')
        return
    size = os.path.getsize(path)
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM users')
        u = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM transactions')
        t = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM groups')
        g = cur.fetchone()[0]
        conn.close()
        print(f'[DB] {label}: {path} ({size} bytes) users={u} transactions={t} groups={g}')
    except Exception as e:
        print(f'[DB] {label}: {path} ({size} bytes) 读取失败: {e}')


def check_port(port):
    try:
        r = subprocess.run(
            ['netstat', '-ano'], capture_output=True, text=True, timeout=5
        )
        lines = [l for l in r.stdout.splitlines() if f':{port} ' in l and 'LISTENING' in l]
        if lines:
            pids = set(l.strip().split()[-1] for l in lines)
            print(f'[端口] :{port} → LISTENING (PID={list(pids)})')
            return True
        else:
            print(f'[端口] :{port} → 未监听')
            return False
    except Exception as e:
        print(f'[端口] :{port} → 检查失败: {e}')
        return False


def check_http(port):
    try:
        import httpx
        r = httpx.get(f'http://127.0.0.1:{port}/hive/info', timeout=2, trust_env=False)
        print(f'[HTTP] :{port}/hive/info → {r.status_code} {r.text[:120]}')
    except Exception as e:
        print(f'[HTTP] :{port}/hive/info → 失败: {e}')


def main():
    print('=' * 60)
    print('SASES 主节点候选检查')
    print('=' * 60)
    print()
    print('--- 数据库文件 ---')
    for label, path in DB_CANDIDATES:
        check_db(label, path)
    print()
    print('--- 端口占用 ---')
    for port in PORTS:
        check_port(port)
    print()
    print('--- HTTP 响应 ---')
    for port in PORTS:
        check_http(port)
    print()
    print('=' * 60)


if __name__ == '__main__':
    main()
