import re

FP = "core/services/swarm/prompts.py"
with open(FP, 'r', encoding='utf-8') as f:
    content = f.read()

m = re.search(r'COMMANDER_SYSTEM_PROMPT = """(.*?)"""', content, re.DOTALL)
p = m.group(1)

print(f"总字符: {len(p)}\n")

# 精确分段：只在 \n 后第一个字符是【时切
parts = re.split(r'\n(?=【)', p)
sections = []
for part in parts:
    m2 = re.match(r'(【[^】]+】)', part)
    if m2:
        title = m2.group(1)
        sections.append((title, len(part), part))

print(f"共 {len(sections)} 段\n")

# 检查：每一段前 200 字符 + 后 100 字符
for i, (title, length, body) in enumerate(sections, 1):
    head = body[:200].replace('\n', ' \\n ')[:180]
    print(f"[{i:02d}] {title} ({length}字符)")
    print(f"     {head}")
    print()