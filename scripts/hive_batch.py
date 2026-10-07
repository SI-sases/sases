"""批量启动蜂巢轻量节点。

用法：
    python scripts/hive_batch.py --count 9 --port-base 9001 --master http://127.0.0.1:8001
"""
import argparse
import subprocess
import sys
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=10)
    parser.add_argument('--port-base', type=int, default=9001)
    args = parser.parse_args()

    count = args.count
    port_base = args.port_base
    hive_dir = 'D:/sases-hive'
    Path(hive_dir).mkdir(parents=True, exist_ok=True)

    all_ports = [port_base + i for i in range(count)]

    procs = []
    for i in range(count):
        node_id = f'node-{chr(65 + i) if i < 26 else i}'
        port = port_base + i
        db = f'{hive_dir}/{node_id}.db'
        peers = ','.join([f'http://127.0.0.1:{p}' for p in all_ports if p != port])

        log_path = f'{hive_dir}/{node_id}.log'
        log_f = open(log_path, 'w', encoding='utf-8')

        cmd = [
            sys.executable, 'scripts/hive_sim.py',
            '--node-id', node_id,
            '--db', db,
            '--port', str(port),
            '--peers', peers,
        ]
        p = subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT, cwd=os.getcwd())
        procs.append((node_id, port, p, log_f))
        print(f'[{node_id}] started on port {port}, log: {log_path}')

    print(f'Total {count} nodes launched. Logs in {hive_dir}/node-*.log')
    print('Press Ctrl+C to stop all nodes.')

    try:
        for node_id, port, p, _ in procs:
            p.wait()
    except KeyboardInterrupt:
        print('Shutting down...')
        for node_id, port, p, log_f in procs:
            try:
                p.terminate()
                log_f.close()
            except Exception:
                pass
        print('Done.')


if __name__ == '__main__':
    main()
