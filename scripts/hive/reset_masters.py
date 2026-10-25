"""reset_masters.py —— 备份并清空 8002/8003 的旧数据。

用法：
    python scripts/hive/reset_masters.py
"""
import os
import shutil
from datetime import datetime

CANDIDATES = [
    ('8002', 'D:/sases1/users.db'),
    ('8003', 'D:/sases2/users.db'),
]

BACKUP_DIR = 'hive-nodes/_backups'


def main():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')

    for label, path in CANDIDATES:
        if not os.path.exists(path):
            print(f'[{label}] {path} 不存在，跳过')
            continue
        backup = os.path.join(BACKUP_DIR, f'{label}_users_{ts}.db')
        shutil.copy2(path, backup)
        size_mb = os.path.getsize(backup) / 1024 / 1024
        print(f'[{label}] 已备份 → {backup} ({size_mb:.1f}MB)')
        os.remove(path)
        print(f'[{label}] 已清空 {path}')

    print('[完成]')


if __name__ == '__main__':
    main()
