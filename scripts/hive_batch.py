"""批量启动蜂巢轻量节点。

用法：
    python scripts/hive_batch.py --count 9 --port-base 9001 --master http://127.0.0.1:8001
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=9)
    parser.add_argument('--port-base', type=int, default=9001)
    parser.add_argument('--master', type=str, default='http://127.0.0.1:8001')
    args = parser.parse_args()

    count = args.count
    port_base = args.port_base
    master = args.master.rstrip('/')
    log_dir = Path('hive-nodes/_logs')
    log_dir.mkdir(parents=True, exist_ok=True)

    procs = []
    for i in range(count):
        node_id = f'node-{i+1:02d}'
        port = port_base + i
        log_path = log_dir / f'{node_id}.log'
        log_f = open(log_path, 'w', encoding='utf-8')

        env = os.environ.copy()
        env['HIVE_ROLE'] = 'slave'
        env['ENABLE_HIVE'] = 'true'
        env['SASES_PORT'] = str(port)
        env['SASES_NODE_ID'] = node_id
        env['HIVE_MASTER'] = master

        cmd = [sys.executable, '-m', 'core.hive.standalone']
        p = subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT, cwd=os.getcwd(), env=env)
        procs.append((node_id, port, p, log_f))
        print(f'[{node_id}] started on port {port}, log: {log_path}')

    print(f'Total {count} nodes launched. Master: {master}')
    print('Press Ctrl+C to stop all nodes.')

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
