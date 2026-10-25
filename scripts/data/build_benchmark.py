# -*- coding: utf-8 -*-
"""
从 success_kb.json 构建评测集 eval_benchmark.jsonl
- 全部 13 条有 test_cases 的任务（精确验证）
- 从有真实 branch_a 的代码任务中抽 87 条（LLM 评判）
"""
import json
import re
import random

random.seed(42)  # 固定随机种子，保证可复现

KB_FILE = "success_kb.json"
OUT_FILE = "eval_benchmark.jsonl"

def is_code_task(task_text, solution_text):
    """判断是否是代码任务"""
    code_patterns = [r'\bdef\s+\w+\s*\(', r'\bclass\s+\w+', r'import\s+\w+']
    for p in code_patterns:
        if re.search(p, solution_text):
            return True
    return False

def main():
    with open(KB_FILE, "r", encoding="utf-8") as f:
        kb = json.load(f)

    print(f"知识库总数: {len(kb)}")

    # 分类
    with_tests = []
    code_tasks_no_tests = []
    for i, entry in enumerate(kb):
        if entry.get("test_cases"):
            with_tests.append(entry)
        elif is_code_task(entry["task"], entry.get("solution", "")):
            # 只保留有真实 branch_a 的（非默认值）
            if entry.get("branch_a") and entry["branch_a"] != "默认算法A":
                code_tasks_no_tests.append(entry)

    print(f"有 test_cases 的任务: {len(with_tests)}")
    print(f"有真实 branch_a 的代码任务: {len(code_tasks_no_tests)}")

    # 抽取 87 条代码任务（不足则全取）
    sample_size = min(87, len(code_tasks_no_tests))
    sampled = random.sample(code_tasks_no_tests, sample_size)
    print(f"抽取代码任务: {sample_size}")

    # 合并
    benchmark = with_tests + sampled
    print(f"评测集总数: {len(benchmark)}")

    # 写入
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        for i, entry in enumerate(benchmark):
            record = {
                "benchmark_id": i,
                "task": entry["task"],
                "reference_solution": entry.get("solution", ""),
                "test_cases": entry.get("test_cases", []),
                "has_test_cases": bool(entry.get("test_cases")),
                "source_id": entry.get("id", ""),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"已保存到 {OUT_FILE}")
    print(f"  - 有测试用例: {len(with_tests)}")
    print(f"  - 仅 LLM 评判: {sample_size}")

if __name__ == "__main__":
    main()
