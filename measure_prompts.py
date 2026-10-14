import re

FP = "core/services/swarm/prompts.py"
with open(FP, 'r', encoding='utf-8') as f:
    content = f.read()

# 提取 COMMANDER_SYSTEM_PROMPT
m = re.search(r'COMMANDER_SYSTEM_PROMPT = """(.*?)"""', content, re.DOTALL)
if not m:
    print("没找到 COMMANDER_SYSTEM_PROMPT")
    exit(1)

prompt = m.group(1)
print(f"COMMANDER_SYSTEM_PROMPT 总字符: {len(prompt)}")
print()

# 按【】分段
parts = re.split(r'(?=【)', prompt)
sections = []
for p in parts:
    m2 = re.match(r'(【[^】]+】)', p)
    if m2:
        title = m2.group(1)
        sections.append((title, len(p)))

# 排序
sections.sort(key=lambda x: -x[1])

print(f"共 {len(sections)} 段。按字符数排序（前 25）：")
print()
for i, (title, length) in enumerate(sections[:25], 1):
    print(f"  {i:2d}. [{length:5d}] {title}")

print()
print("=== 全部段落的标题（按原文顺序） ===")
# 按原文顺序
orig_order = []
for p in parts:
    m2 = re.match(r'(【[^】]+】)', p)
    if m2:
        orig_order.append(m2.group(1))
for i, title in enumerate(orig_order, 1):
    print(f"  {i:2d}. {title}")