"""start_masters.py —— 启动 8002/8003 两个轻量主节点。

用法：
    python scripts/hive/start_masters.py
"""
import os
import subprocess
import sys
from pathlib import Path

MASTERS = [
    {'node_id': 'node-B', 'port': 8002},
    {'node_id': 'node-C', 'port': 8003},
]
AUTHORITY = 'http://127.0.0.1:8001'


def main():
    log_dir = Path('hive-nodes/_logs')
    log_dir.mkdir(parents=True, exist_ok=True)

    procs = []
    for m in MASTERS:
        node_id = m['node_id']
        port = m['port']
        log_path = log_dir / f'{node_id}.log'
        log_f = open(log_path, 'w', encoding='utf-8')

        env = os.environ.copy()
        env['HIVE_ROLE'] = 'master'
        env['ENABLE_HIVE'] = 'true'
        env['SASES_PORT'] = str(port)
        env['SASES_NODE_ID'] = node_id
        env['HIVE_AUTHORITY'] = AUTHORITY
        env['SASES_DISABLE_FK'] = 'true'
        env['HIVE_PEERS'] = 'http://127.0.0.1:8001,http://127.0.0.1:8002,http://127.0.0.1:8003'

        cmd = [sys.executable, '-m', 'core.hive.standalone_master']
        p = subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT, cwd=os.getcwd(), env=env)
        procs.append((node_id, port, p, log_f))
        print(f'[{node_id}] started on :{port}, log: {log_path}')

    print(f'\nTotal {len(MASTERS)} masters launched. Authority: {AUTHORITY}')
    print('Press Ctrl+C to stop all masters.')

    try:
        for _, _, p, _ in procs:
            p.wait()
    except KeyboardInterrupt:
        print('Shutting down...')
        for _, _, p, log_f in procs:
            try:
                p.terminate()
                log_f.close()
            except Exception:
                pass
        print('Done.')


if __name__ == '__main__':
    main()
