# -*- coding: utf-8 -*-
import sqlite3

def read_file(path):
    try:
        return open(path, encoding="utf-8").read()
    except Exception as e:
        return "[ERR] " + str(e)

def find_func(src, name, max_len=3500):
    i = src.find("def " + name)
    if i < 0:
        i = src.find("async def " + name)
    if i < 0:
        return "[NOT FOUND] " + name
    j = src.find("\ndef ", i + 10)
    if j < 0:
        j = src.find("\nasync def ", i + 10)
    if j < 0:
        j = len(src)
    return src[i:j][:max_len]

print("=" * 70)
print("A. commander.enrich_plan_input（完整）")
print("=" * 70)
c = read_file("core/services/swarm/commander.py")
print(find_func(c, "enrich_plan_input", 3500))

print("=" * 70)
print("B. commander.plan_task 的 return 语句（只看 return 相关行）")
print("=" * 70)
i = c.find("async def plan_task")
if i < 0:
    i = c.find("def plan_task")
j = c.find("\nasync def ", i + 10)
if j < 0:
    j = c.find("\ndef ", i + 10)
if j < 0:
    j = len(c)
fn = c[i:j]
lines = fn.split("\n")
for k, line in enumerate(lines, 1):
    s = line.strip()
    if any(x in s for x in ("return ", "plan_result", "human_summary", "machine_steps", "json.dumps", "json.loads")) or s.startswith("return {"):
        print(f"  L{k}: {s[:180]}")

print("=" * 70)
print("C. prompts.COMMANDER_SYSTEM_PROMPT 最后 2000 字")
print("=" * 70)
p = read_file("core/services/swarm/prompts.py")
i = p.find('COMMANDER_SYSTEM_PROMPT = """')
if i < 0:
    i = p.find("COMMANDER_SYSTEM_PROMPT = '''")
if i < 0:
    print("[NOT FOUND]")
else:
    # 找结尾
    q = '"""' if '"""' in p[i:i+50] else "'''"
    j = p.find(q, i + len("COMMANDER_SYSTEM_PROMPT = " + q))
    if j < 0:
        j = i + 8000
    block = p[i:j+3]
    print(f"总长度: {len(block)}")
    print("最后 2000 字:")
    print(block[-2000:])

print("=" * 70)
print("D. decider.task_summarizer 的 return 语句")
print("=" * 70)
d = read_file("core/services/supervisor/decider.py")
i = d.find("async def task_summarizer")
if i < 0:
    i = d.find("def task_summarizer")
j = d.find("\nasync def ", i + 10)
if j < 0:
    j = d.find("\ndef ", i + 10)
if j < 0:
    j = len(d)
fn = d[i:j]
lines = fn.split("\n")
for k, line in enumerate(lines, 1):
    s = line.strip()
    if "return " in s and ("goal_achieved" in s or "reason" in s or "hint" in s or "{" in s):
        print(f"  L{k}: {s[:200]}")
    if s.startswith("return {"):
        # 打印接下来 6 行
        for m in range(k-1, min(k+6, len(lines))):
            print(f"  L{m+1}: {lines[m].strip()[:160]}")

print("=" * 70)
print("E. send.py 里 plan_result / answer 的用法")
print("=" * 70)
s = read_file("core/services/message/send.py")
lines = s.split("\n")
for k, line in enumerate(lines, 1):
    if any(x in line for x in ("plan_result", "supervisor_service.create_run", "dispatch_task", "dispatch_run", "auto_run 已派单", "message\": ")):
        print(f"  L{k}: {line.strip()[:160]}")
# 也看 plan_result 后面 5 行
for k, line in enumerate(lines, 1):
    if "plan_result" in line:
        for m in range(k-1, min(k+8, len(lines))):
            print(f"  L{m+1}: {lines[m].strip()[:160]}")
        break

print("=" * 70)
print("F. safety_memory 的 task_result / task_summary 样例")
print("=" * 70)
try:
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    for mt in ("task_result", "task_summary"):
        cur.execute("SELECT task_id, substr(content,1,250) AS c FROM safety_memory WHERE memory_type=? ORDER BY id DESC LIMIT 2", (mt,))
        rows = cur.fetchall()
        print(f"\n[{mt}] 共 {len(rows)} 条:")
        for r in rows:
            print(f"  task_id={r['task_id']}")
            print(f"  content={r['c']}")
    conn.close()
except Exception as e:
    print("[ERR] " + str(e))

print("=" * 70)
print("G. 现有 messages 表 task 相关 msg_type")
print("=" * 70)
try:
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT msg_type, COUNT(*) AS n FROM messages GROUP BY msg_type ORDER BY n DESC")
    for r in cur.fetchall():
        print(f"  {r['msg_type']}: {r['n']}")
    conn.close()
except Exception as e:
    print("[ERR] " + str(e))

print("=" * 70)
print("[DONE] 把完整输出贴回")
print("=" * 70)