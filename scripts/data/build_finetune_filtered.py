# -*- coding: utf-8 -*-
import json

with open("success_kb.json", "r", encoding="utf-8") as f:
    kb = json.load(f)

def clean(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()

records = []
for e in kb:
    task = e.get("task", "").strip()
    sol = e.get("solution", "").strip()
    if not task or not sol:
        continue
    sol_clean = clean(sol)
    # 只保留长度 < 500 的简洁样本
    if len(sol_clean) > 500:
        continue
    records.append({
        "messages": [
            {"role": "user", "content": f"任务：{task}\n请写出一个完整可运行的Python函数。只需输出代码。"},
            {"role": "assistant", "content": sol_clean}
        ]
    })

with open("finetune_filtered.jsonl", "w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"生成 {len(records)} 条训练数据 → finetune_filtered.jsonl")
