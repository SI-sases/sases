# -*- coding: utf-8 -*-
"""批次修复：A（诊断类豁免）+ C（排查问症状）+ B（查 loop-guard）"""
import ast
import re

results = []

def read(path):
    try:
        return open(path, encoding="utf-8").read()
    except Exception:
        return None

def write(path, content):
    open(path, "w", encoding="utf-8").write(content)

# ============ A: decider.py 加诊断类豁免 ============
print("=" * 60)
print("[A] R3 诊断类豁免（排查类任务不要求写代码）")
print("=" * 60)

F_A = "core/services/supervisor/decider.py"
c = read(F_A)
if not c:
    print("[ERR] 读不到 decider.py")
    results.append(("A", "ERR"))
elif "_is_diagnosis_task" in c:
    print("[SKIP] A 已存在")
    results.append(("A", "SKIP"))
else:
    m = re.search(r'(?m)^([ \t]*)(_need_patch\s*=\s*any\([^\n]*)', c)
    if not m:
        print("[ERR] _need_patch 锚点未找到")
        idx = c.find("_need_patch")
        if idx >= 0:
            print("现有内容:")
            print(c[max(0, idx - 200):idx + 400])
        results.append(("A", "ERR"))
    else:
        indent = m.group(1)
        original_line = m.group(2)
        replacement = (
            f"{indent}_user_original = task.get('user_text', '') or ''\n"
            f"{indent}_is_diagnosis_task = any(k in _user_original[:30] for k in ('看下', '看看', '查下', '查一下', '为什么', '怎么回事', '什么原因', '哪里不对', '帮我看看'))\n"
            f"{indent}if _is_diagnosis_task:\n"
            f"{indent}    _need_patch = False\n"
            f"{indent}else:\n"
            f"{indent}    {original_line}"
        )
        c2 = c.replace(m.group(0), replacement, 1)
        try:
            ast.parse(c2)
            write(F_A, c2)
            print("[OK] A 已改：诊断类任务豁免")
            results.append(("A", "OK"))
        except SyntaxError as e:
            print(f"[ERR] 语法: {e}")
            results.append(("A", "ERR"))

# ============ C: prompts.py 加排查类必须问症状 ============
print("=" * 60)
print("[C] 排查类必须问症状铁律")
print("=" * 60)

F_C = "core/services/swarm/prompts.py"
c = read(F_C)
if not c:
    print("[ERR] 读不到 prompts.py")
    results.append(("C", "ERR"))
elif "【排查类任务必须确认症状（v2）】" in c:
    print("[SKIP] C 已存在")
    results.append(("C", "SKIP"))
else:
    NEW_C = """

【排查类任务必须确认症状（v2）】
如果用户问"为什么不行/怎么回事/看下哪里不对"，且侦察发现多个可能原因：
1. 列出 2-3 个可能原因（带 file:line）
2. 问用户具体症状："你删除时看到什么？按钮没反应/报错弹窗/删完列表还在"
3. 禁止只报"XX 代码是对的"就结束
4. 禁止把排查任务当成修复任务硬写代码
"""
    start_marker = 'COMMANDER_SYSTEM_PROMPT = """'
    i = c.find(start_marker)
    if i < 0:
        print("[ERR] COMMANDER_SYSTEM_PROMPT 未找到")
        results.append(("C", "ERR"))
    else:
        j = c.find('"""', i + len(start_marker))
        if j < 0:
            print("[ERR] 结束三引号未找到")
            results.append(("C", "ERR"))
        else:
            c2 = c[:j] + NEW_C + c[j:]
            try:
                ast.parse(c2)
                write(F_C, c2)
                print("[OK] C 已改：排查类问症状铁律")
                results.append(("C", "OK"))
            except SyntaxError as e:
                print(f"[ERR] 语法: {e}")
                results.append(("C", "ERR"))

# ============ B: 查 loop-guard 和假修复消息来源 ============
print("=" * 60)
print("[B] 查 loop-guard 和假修复消息来源")
print("=" * 60)

SEARCH_FILES = [
    "core/services/supervisor/continuation.py",
    "core/services/supervisor/decider.py",
    "core/services/supervisor/runs.py",
    "core/services/swarm/executor_callback.py",
    "core/services/swarm/summarizer.py",
]
KEYWORDS = ["loop-guard", "MODIFY chain", "retry limit reached", "已完成修改", "已修复"]

for f in SEARCH_FILES:
    cc = read(f)
    if not cc:
        continue
    hits = [kw for kw in KEYWORDS if kw in cc]
    if hits:
        print(f"\n[{f}] 命中: {hits}")
        idx = cc.find("MODIFY chain")
        if idx >= 0:
            print(f"  MODIFY chain 上下文:")
            print(cc[max(0, idx - 400):idx + 500])
        idx2 = cc.find("retry limit reached")
        if idx2 >= 0:
            print(f"  retry limit 上下文:")
            print(cc[max(0, idx2 - 300):idx2 + 300])

# ============ 汇总 ============
print()
print("=" * 60)
print("[汇总]")
for name, status in results:
    print(f"  {name}: {status}")
print("=" * 60)
print("[提示] A/C OK 或 SKIP 即可重启；B 需根据上下文决定修复位置")