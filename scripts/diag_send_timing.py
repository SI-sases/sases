"""diag_send_timing.py —— 测 8001 处理 /messages/send 的耗时。"""
import httpx
import time

# 拿 token
r = httpx.post('http://127.0.0.1:8001/token', data={'username': '666666', 'password': '123456'}, timeout=5, trust_env=False)
token = r.json()['access_token']
print('token ok')

# 测 5 次
times = []
for i in range(5):
    start = time.time()
    try:
        r = httpx.post('http://127.0.0.1:8001/messages/send',
                       json={'content': f'timing-test-{i}'},
                       headers={'Authorization': f'Bearer {token}'},
                       timeout=90, trust_env=False)
        elapsed = time.time() - start
        times.append(elapsed)
        print(f'attempt {i+1}: {r.status_code}, {elapsed:.2f}s')
    except Exception as e:
        elapsed = time.time() - start
        print(f'attempt {i+1}: exception {type(e).__name__}, {elapsed:.2f}s')

if times:
    print()
    print(f'min: {min(times):.2f}s, max: {max(times):.2f}s, avg: {sum(times)/len(times):.2f}s')