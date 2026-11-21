# -*- coding: utf-8 -*-
"""diag2: 查 create_run 签名 / _save_pending 实现 / plan_task task 构建 / model_call 签名"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

def sec(t):
    print('\n' + '='*70)
    print(t)
    print('='*70)

# 1. create_run 完整签名
sec('1. create_run 完整签名')
p = os.path.join(ROOT, 'core/services/supervisor/runs.py')
if os.path.exists(p):
    c = open(p, encoding='utf-8').read()
    i = c.find('def create_run')
    if i >= 0:
        j = c.find('\ndef ', i+10)
        if j < 0: j = i + 1500
        print(c[i:j])
    else:
        print('[NOT FOUND]')
else:
    print('[FILE NOT FOUND]')

# 2. _save_pending 完整实现
sec('2. _save_pending 完整实现')
p = os.path.join(ROOT, 'core/services/swarm/commander.py')
c_cm = open(p, encoding='utf-8').read() if os.path.exists(p) else ''
if c_cm:
    i = c_cm.find('def _save_pending')
    if i >= 0:
        j = c_cm.find('\ndef ', i+10)
        if j < 0: j = i + 2500
        print(c_cm[i:j])
    else:
        print('[NOT FOUND]')

# 3. plan_task 里 task dict 构建 + _save_pending 调用 + supervisor_run_id 出现
sec('3. plan_task 里 task 构建 & supervisor_run_id 出现行')
if c_cm:
    i = c_cm.find('async def plan_task')
    j = c_cm.find('\nasync def ', i+20)
    if j < 0: j = len(c_cm)
    body = c_cm[i:j]
    for k, line in enumerate(body.split('\n'), 1):
        if ('task =' in line or '_save_pending' in line or 'supervisor_run_id' in line) and 'def ' not in line:
            print(f'{k}: {line.rstrip()[:200]}')

# 4. model_call.py 的 call_model_with_config
sec('4. model_call.py 的 call_model_with_config')
p = os.path.join(ROOT, 'core/services/message/model_call.py')
if os.path.exists(p):
    c = open(p, encoding='utf-8').read()
    i = c.find('def call_model_with_config')
    if i < 0:
        i = c.find('async def call_model_with_config')
    if i >= 0:
        lines = c[i:].split('\n')[:45]
        print('\n'.join(lines))
    else:
        print('[NOT FOUND] 文件里所有 def/async def：')
        for k, line in enumerate(c.split('\n'), 1):
            s = line.strip()
            if s.startswith('def ') or s.startswith('async def '):
                print(f'{k}: {s}')
else:
    print('[FILE NOT FOUND]')
