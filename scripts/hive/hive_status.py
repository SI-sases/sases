"""hive_status.py —— 一览所有节点状态。

用法：
    python scripts/hive/hive_status.py
"""
import os
import sys
import httpx
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.hive.registry import list_nodes


def fetch_status(url):
    try:
        r = httpx.get(f'{url}/hive/status', timeout=2, trust_env=False)
        return r.json()
    except Exception as e:
        return {'error': str(e)}


def main():
    nodes = list_nodes()
    # 加自己
    my_url = f"http://127.0.0.1:{os.environ.get('SASES_PORT', '8001')}"
    nodes.insert(0, {'node_id': 'self', 'url': my_url, 'role': 'master'})

    print(f"{'node_id':<12} {'role':<8} {'hash':<18} {'sync':<16} {'degraded':<10}")
    print('-' * 70)

    for n in nodes:
        url = n.get('url', '')
        data = fetch_status(url)
        node_id = data.get('node_id', n.get('node_id', '?'))
        role = data.get('role', n.get('role', '?'))
        if data.get('replica_mode'):
            role = role + '/replica'
        sync = data.get('sync') or {}
        last_ok = sync.get('last_sync_ok')
        fails = sync.get('consecutive_failures', '?')
        degraded = sync.get('degraded', '?')
        anchor = data.get('latest_anchor') or {}
        h = (anchor.get('anchor_hash') or '')[:16]
        sync_str = f"ok={last_ok} fails={fails}"
        print(f"{node_id:<12} {role:<8} {h:<18} {sync_str:<16} {str(degraded):<10}")


if __name__ == '__main__':
    main()
