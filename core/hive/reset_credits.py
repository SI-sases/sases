"""reset_credits.py —— 清空积分相关数据，跑前自动备份。

用法（在项目根目录）：
    python core/hive/reset_credits.py
"""
import os
import shutil
import sqlite3
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = os.path.join(ROOT, 'users.db')


def main():
    if not os.path.exists(DB):
        print(f'[error] 找不到 {DB}')
        return

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = os.path.join(ROOT, f'users_before_credit_reset_{ts}.db')
    shutil.copy2(DB, backup)
    print(f'[备份] {backup} ({os.path.getsize(backup)} bytes)')

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*), COALESCE(SUM(credits),0) FROM users')
    u_cnt, u_sum = cur.fetchone()
    cur.execute('SELECT COUNT(*) FROM contribution_log')
    c_cnt = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM credit_anchors')
    a_cnt = cur.fetchone()[0]
    print(f'[清空前] users有积分: {u_cnt}人 总和={u_sum}  contribution_log={c_cnt}  credit_anchors={a_cnt}')

    cur.execute('UPDATE users SET credits = 0')
    cur.execute('DELETE FROM contribution_log')
    cur.execute('DELETE FROM credit_anchors')
    try:
        cur.execute('DELETE FROM credit_pool')
        pool = 'yes'
    except Exception:
        pool = 'no table'
    conn.commit()

    cur.execute('SELECT COALESCE(SUM(credits),0) FROM users')
    s = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM contribution_log')
    c = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM credit_anchors')
    a = cur.fetchone()[0]
    print(f'[清空后] users积分总和={s}  contribution_log={c}  credit_anchors={a}  credit_pool={pool}')
    conn.close()
    print('[完成]')


if __name__ == '__main__':
    main()
