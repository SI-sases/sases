# -*- coding: utf-8 -*-
import json
import re

with open("success_kb.json", "r", encoding="utf-8") as f:
    kb = json.load(f)

print(f"知识库总数: {len(kb)}")

# 按 id 顺序推断：前 474 条 vs 后 256 条
old_474 = kb[:474]
new_256 = kb[474:]

def analyze(entries, name):
    print(f"\n===== {name}（{len(entries)} 条）=====")
    
    # 含代码比例
    with_code = sum(1 for e in entries if re.search(r'def\s+\w+', e.get('solution', '')))
    print(f"含Python函数: {with_code} ({with_code/len(entries)*100:.1f}%)")
    
    # 平均长度
    avg_len = sum(len(e.get('solution', '')) for e in entries) / len(entries)
    print(f"平均长度: {avg_len:.0f} 字符")
    
    # 超长
    over_1000 = sum(1 for e in entries if len(e.get('solution', '')) > 1000)
    print(f"超过1000字符: {over_1000} ({over_1000/len(entries)*100:.1f}%)")
    
    # 含 markdown 的
    with_md = sum(1 for e in entries if '```' in e.get('solution', ''))
    print(f"含 markdown 标记: {with_md} ({with_md/len(entries)*100:.1f}%)")
    
    # 是否有 branch_a
    with_branch = sum(1 for e in entries if e.get('branch_a') and e['branch_a'] != '默认算法A')
    print(f"有真实 branch_a: {with_branch}")
    
    # 样例
    print(f"\n前3条任务描述:")
    for e in entries[:3]:
        print(f"  - {e['task'][:70]}")

analyze(old_474, "前474条（推测为474版本训练数据）")
analyze(new_256, "后256条（推测为新增数据）")

# 检查两者的代码风格差异
print("\n\n===== 代码风格对比 =====")
def style_stats(entries, name):
    with_type_hint = sum(1 for e in entries if re.search(r'def \w+\([^)]*:\s*(int|str|list|float|bool)', e.get('solution', '')))
    with_docstring = sum(1 for e in entries if '"""' in e.get('solution', '') or "'''" in e.get('solution', ''))
    with_comment = sum(1 for e in entries if re.search(r'#.*\n', e.get('solution', '')))
    print(f"\n{name}:")
    print(f"  含类型提示: {with_type_hint}")
    print(f"  含 docstring: {with_docstring}")
    print(f"  含注释: {with_comment}")

style_stats(old_474, "前474条")
style_stats(new_256, "后256条")
