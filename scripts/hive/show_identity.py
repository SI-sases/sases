"""show_identity.py —— 显示当前节点的公钥和指纹。

用法：
    set SASES_NODE_ID=node-A
    python scripts/hive/show_identity.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.hive.identity import get_public_key_b64, get_key_fingerprint, sign, verify


def main():
    node_id = os.environ.get('SASES_NODE_ID', 'node-A')
    pub = get_public_key_b64(node_id)
    fp = get_key_fingerprint(node_id)
    print(f'node_id: {node_id}')
    print(f'fingerprint: {fp}')
    print(f'public_key: {pub}')

    # 自签自验
    msg = 'hello-hive'
    sig = sign(node_id, msg)
    ok = verify(pub, sig, msg)
    print(f'self-verify: {ok}')

    # 错误数据的验签
    bad = verify(pub, sig, 'wrong-message')
    print(f'wrong-verify: {bad} (expect False)')


if __name__ == '__main__':
    main()
