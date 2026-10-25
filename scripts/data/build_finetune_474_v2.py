# -*- coding: utf-8 -*-
import json

with open("success_kb.json", "r", encoding="utf-8") as f:
    kb = json.load(f)[:474]

EOS = "</s>"

def make_training_text(user_content, assistant_content):
    return f"<|user|>\n{user_content}{EOS}<|assistant|>\n{assistant_content}{EOS}"

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
    user_content = f"任务：{task}\n请写出一个完整可运行的Python函数。只需输出代码。"
    assistant_content = clean(sol)
    records.append({"text": make_training_text(user_content, assistant_content)})

with open("finetune_474_chat.jsonl", "w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"生成 {len(records)} 条 -> finetune_474_chat.jsonl")
print("样例 text 前 400 字符:")
print(repr(records[0]["text"][:400]))
print()
print("包含 <|user|>:", "<|user|>" in records[0]["text"])
print("包含 <|assistant|>:", "<|assistant|>" in records[0]["text"])