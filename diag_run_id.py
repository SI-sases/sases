# -*- coding: utf-8 -*-
"""诊断 run_id=None 根因 + 找 model_service 真实的调用函数名"""
import os, re, sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = []

def log(s):
    OUT.append(str(s))

# ========== [1] 谁调了 create_run，返回值去哪了 ==========
log("=" * 60)
log("[1] create_run 调用点 + 上下文 20 行")
log("=" * 60)
for f in ['core/services/swarm/commander.py', 'core/services/message/send.py', 
          'core/services/supervisor/runs.py', 'core/services/swarm/executor_callback.py']:
    p = os.path.join(ROOT, f)
    if not os.path.exists(p):
        continue
    c = open(p, encoding='utf-8').read()
    lines = c.split('\n')
    for i, line in enumerate(lines, 1):
        if 'create_run' in line and 'def ' not in line:
            log(f"\n--- {f}:{i} ---")
            for j in range(max(0, i-3), min(len(lines), i+8)):
                log(f"{j+1}: {lines[j].rstrip()[:180]}")

# ========== [2] _run_id 赋值与使用 ==========
log("\n" + "=" * 60)
log("[2] _run_id 赋值点（executor_callback.py）")
log("=" * 60)
p = os.path.join(ROOT, 'core/services/swarm/executor_callback.py')
if os.path.exists(p):
    c = open(p, encoding='utf-8').read()
    lines = c.split('\n')
    for i, line in enumerate(lines, 1):
        if '_run_id' in line and '=' in line and '==' not in line and '!=' not in line:
            log(f"{i}: {line.rstrip()[:180]}")

# ========== [3] supervisor_runs 最近记录 ==========
log("\n" + "=" * 60)
log("[3] supervisor_runs 最近 5 条")
log("=" * 60)
try:
    conn = sqlite3.connect(os.path.join(ROOT, 'users.db'))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, user_id, conversation_id, status, created_at FROM supervisor_runs ORDER BY id DESC LIMIT 5")
    for r in cur.fetchall():
        log(dict(r))
    cur.execute("SELECT COUNT(*) FROM supervisor_runs")
    log("总记录数: " + str(cur.fetchone()[0]))
    conn.close()
except Exception as e:
    log("ERR: " + str(e))

# ========== [4] plan_task 返回值里有没有 supervisor_run_id ==========
log("\n" + "=" * 60)
log("[4] plan_task 的 return 语句")
log("=" * 60)
p = os.path.join(ROOT, 'core/services/swarm/commander.py')
if os.path.exists(p):
    c = open(p, encoding='utf-8').read()
    # 找 plan_task 函数体
    i = c.find('async def plan_task')
    if i >= 0:
        # 找下一个顶层 def
        j = c.find('\nasync def ', i + 20)
        if j < 0: j = c.find('\ndef ', i + 20)
        if j < 0: j = len(c)
        func_body = c[i:j]
        lines = func_body.split('\n')
        for k, line in enumerate(lines, 1):
            if 'return' in line and ('status' in line or 'supervisor_run' in line or 'task_id' in line):
                log(f"{k}: {line.rstrip()[:220]}")

# ========== [5] send.py 收到 plan_result 后怎么处理 ==========
log("\n" + "=" * 60)
log("[5] send.py 里 plan_result / supervisor_run_id 相关处理")
log("=" * 60)
p = os.path.join(ROOT, 'core/services/message/send.py')
if os.path.exists(p):
    c = open(p, encoding='utf-8').read()
    lines = c.split('\n')
    for i, line in enumerate(lines, 1):
        if ('plan_result' in line or 'supervisor_run_id' in line) and 'plan_result=' not in line[:30]:
            log(f"{i}: {line.rstrip()[:180]}")

# ========== [6] model_service 里真实调用函数名 ==========
log("\n" + "=" * 60)
log("[6] model_service.py 所有 def 行")
log("=" * 60)
p = os.path.join(ROOT, 'core/services/model_service.py')
if os.path.exists(p):
    c = open(p, encoding='utf-8').read()
    for i, line in enumerate(c.split('\n'), 1):
        if line.strip().startswith('def ') or line.strip().startswith('async def '):
            log(f"{i}: {line.strip()[:180]}")

# ========== [7] 谁调用 model_service 的调用函数 ==========
log("\n" + "=" * 60)
log("[7] 全项目搜 'call_model' / 'chat_completion' 的调用")
log("=" * 60)
for f in ['core/services/swarm/commander.py', 'core/services/swarm/llm_parser.py', 
          'core/services/message/send.py', 'core/services/intent_service.py']:
    p = os.path.join(ROOT, f)
    if not os.path.exists(p):
        continue
    c = open(p, encoding='utf-8').read()
    for i, line in enumerate(c.split('\n'), 1):
        if ('call_model' in line or 'chat_completion' in line or '_call_llm' in line):
            log(f"{f}:{i}: {line.strip()[:180]}")

# 输出
report = '\n'.join(OUT)
print(report)
with open(os.path.join(ROOT, 'diag_run_id_report.txt'), 'w', encoding='utf-8') as f:
    f.write(report)
print("\n[WROTE] diag_run_id_report.txt")
