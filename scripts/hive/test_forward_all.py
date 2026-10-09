"""test_forward_all.py —— 逐个测试写接口转发。

前置：8001 主节点 + 8002 副本都在跑。
用法：python scripts/hive/test_forward_all.py
"""
import httpx
import json

# 从 8002 登录（白名单，本地处理）
BASE = 'http://127.0.0.1:8002'

def login():
    r = httpx.post(f'{BASE}/token', data={'username': '666666', 'password': '123456'}, timeout=5, trust_env=False)
    if r.status_code != 200:
        print('login failed:', r.status_code, r.text)
        return None
    return r.json()['access_token']


def test(token, name, method, path, body=None):
    headers = {'Authorization': f'Bearer {token}'}
    url = f'{BASE}{path}'
    try:
        if method == 'POST':
            r = httpx.post(url, json=body, headers=headers, timeout=15, trust_env=False)
        elif method == 'PUT':
            r = httpx.put(url, json=body, headers=headers, timeout=15, trust_env=False)
        elif method == 'PATCH':
            r = httpx.patch(url, json=body, headers=headers, timeout=15, trust_env=False)
        elif method == 'DELETE':
            r = httpx.delete(url, headers=headers, timeout=15, trust_env=False)
        else:
            print(f'{name}: unsupported method {method}')
            return
        ok = '✅' if r.status_code in (200, 201) else '❌'
        print(f'{ok} {name}: {r.status_code} {r.text[:120]}')
    except Exception as e:
        print(f'❌ {name}: exception {type(e).__name__} {str(e)[:80]}')


def main():
    token = login()
    if not token:
        return
    print(f'logged in, token len = {len(token)}')
    print()
    print('=== 逐个测试写接口（副本→主节点转发）===')
    print()

    # 1. 发消息（已验证）
    test(token, '1. POST /messages/send', 'POST', '/messages/send', {'content': 'stage2 test'})

    # 2. 改用户资料
    test(token, '2. PUT /user/profile', 'PUT', '/user/profile', {'signature': 'stage2 signature'})

    # 3. 写记忆
    test(token, '3. POST /memory/remember', 'POST', '/memory/remember', {
        'memory_type': 'stage2_test',
        'content': 'stage2 test memory',
    })

    # 4. 喂宠物
    test(token, '4. POST /pet/feed', 'POST', '/pet/feed', {'pet_id': 1, 'exp_amount': 5})

    # 5. 标记已读
    test(token, '5. POST /messages/1/read', 'POST', '/messages/1/read', {})

    # 6. 发好友请求
    test(token, '6. POST /agents/friend-request', 'POST', '/agents/friend-request', {'agent_id': 'test-agent'})

    # 7. 积分兑换
    test(token, '7. POST /credits/exchange', 'POST', '/credits/exchange', {'credits': 1})

    # 8. 发红包
    test(token, '8. POST /transfer/red-packet', 'POST', '/transfer/red-packet', {'receiver_id': 5, 'amount': 1, 'message': 'stage2'})

    # 9. 创建群
    test(token, '9. POST /group/create', 'POST', '/group/create', {'name': 'stage2_test_group'})

    # 10. 写工作日志
    test(token, '10. POST /work/execute', 'POST', '/work/execute', {'command': 'echo stage2'})

    print()
    print('=== 完成 ===')


if __name__ == '__main__':
    main()
