import re

FP = "core/services/swarm/prompts.py"
with open(FP, 'r', encoding='utf-8') as f:
    content = f.read()

m = re.search(r'COMMANDER_SYSTEM_PROMPT = """(.*?)"""', content, re.DOTALL)
p = m.group(1)

# 按【】分段
parts = re.split(r'(?=【)', p)
for i, part in enumerate(parts):
    m2 = re.match(r'(【[^】]+】)', part)
    if m2:
        title = m2.group(1)
        # 打印前 100 字符和后 100 字符
        head = part[:150].replace('\n', '\\n')
        tail = part[-100:].replace('\n', '\\n')
        print(f"=== [{i:02d}] {title} ({len(part)} 字符) ===")
        print(f"  头: {head}")
        print(f"  尾: {tail}")
        print()