# -*- coding: utf-8 -*-
"""
从 success_kb.json 生成 finetune_data.jsonl
格式：{"messages": [{"role": "user", "content": "任务：..."}, {"role": "assistant", "content": "..."}]}
"""
import json
import re

KB_FILE = "success_kb.json"
OUT_FILE = "finetune_data.jsonl"

def is_code_solution(text):
    """只保留代码任务，过滤掉证明等非代码内容"""
    if not text:
        return False
    code_patterns = [r'\bdef\s+\w+\s*\(', r'\bclass\s+\w+', r'\bimport\s+\w+']
    for p in code_patterns:
        if re.search(p, text):
            return True
    return False

def clean_solution(text):
    """去除 markdown 代码块标记"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()

def main():
    with open(KB_FILE, "r", encoding="utf-8") as f:
        kb = json.load(f)

    print(f"知识库总数: {len(kb)}")

    records = []
    skipped_non_code = 0
    skipped_empty = 0

    for entry in kb:
        task = entry.get("task", "").strip()
        solution = entry.get("solution", "").strip()

        if not task or not solution:
            skipped_empty += 1
            continue

        if not is_code_solution(solution):
            skipped_non_code += 1
            continue

        solution_clean = clean_solution(solution)
        if not solution_clean:
            skipped_empty += 1
            continue

        records.append({
            "messages": [
                {"role": "user", "content": f"任务：{task}\n请写出一个完整可运行的Python函数。只需输出代码。"},
                {"role": "assistant", "content": solution_clean}
            ]
        })

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"有效训练样本: {len(records)}")
    print(f"跳过（非代码）: {skipped_non_code}")
    print(f"跳过（空内容）: {skipped_empty}")
    print(f"已保存到 {OUT_FILE}")

if __name__ == "__main__":
    main()
