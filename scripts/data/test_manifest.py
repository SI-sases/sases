# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, "core")

from training_manifest import start_run, finalize

# 开始一次模拟训练
run = start_run()
run.record_data("finetune_474.jsonl")
run.record_config(
    base_model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    training_format="User: ...",
    collator="DataCollatorForLanguageModeling",
    max_length=256,
    lora_r=8,
    lora_alpha=32,
    learning_rate=2e-4,
    num_epochs=3,
    random_seed=42,
)

# 模拟训练结束后保存
finalize("test_manifest_output")

# 打印生成的 manifest
import json
with open("test_manifest_output/training_manifest.json", "r", encoding="utf-8") as f:
    print("\n生成的 manifest 内容：")
    print(json.dumps(json.load(f), ensure_ascii=False, indent=2))