# download_model.py
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="Xenova/bge-small-zh-v1.5",
    local_dir="./bge-small-zh-onnx",
    allow_patterns=[
        "onnx/model_int8.onnx",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.txt",
        "special_tokens_map.json",
        "config.json"
    ]
)

print("模型下载完成，保存在 ./bge-small-zh-onnx")
