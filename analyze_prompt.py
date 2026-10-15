import re

FP = "core/services/swarm/prompts.py"
with open(FP, 'r', encoding='utf-8') as f:
    content = f.read()

m = re.search(r'COMMANDER_SYSTEM_PROMPT = """(.*?)"""', content, re.DOTALL)
p = m.group(1)

print(f"COMMANDER_SYSTEM_PROMPT 总字符: {len(p)}\n")

# 按【】分段
parts = re.split(r'(?=【)', p)
sections = []
for part in parts:
    m2 = re.match(r'(【[^】]+】)', part)
    if m2:
        sections.append((m2.group(1), len(part), part))

print(f"共 {len(sections)} 段\n")

# 分类：指挥官专属 / 认知（常识候选）/ 边界（可下沉代码）
# 简单关键词判断
def classify(title, body):
    t = title
    b = body[:500]
    # 边界类
    if any(kw in t for kw in ['禁止', '铁律', '边界', '硬规则', '纪律']):
        return '边界'
    # 认知类
    if any(kw in t for kw in ['前提验证', '改代码三步', '同类问题', '改前必读', '改后必重读', '先定义后调用', '符号插入幂等']):
        return '认知'
    # 指挥官操作类
    if any(kw in t for kw in ['工具', 'harness', 'file_patch', 'file_read', 'grep_code', 'dir_tree', 'run_python', 'api_call', 'web_fetch', 'git_ops', 'verify']):
        return '操作'
    # 其他
    return '其他'

by_cat = {'操作': [], '认知': [], '边界': [], '其他': []}
for title, length, body in sections:
    cat = classify(title, body)
    by_cat[cat].append((title, length))

for cat in ['操作', '认知', '边界', '其他']:
    total = sum(x[1] for x in by_cat[cat])
    print(f"=== {cat} ({len(by_cat[cat])} 段, {total} 字符) ===")
    for title, length in by_cat[cat]:
        print(f"  [{length:5d}] {title}")
    print()