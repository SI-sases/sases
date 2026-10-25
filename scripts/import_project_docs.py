# scripts/import_project_docs.py
"""投喂一份项目文档到项目库

用法:
    python scripts/import_project_docs.py docs/xxx.md v0.17.0
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.services import project_service


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/import_project_docs.py <文件路径> [版本号]")
        return 1

    file_path = sys.argv[1]
    version = sys.argv[2] if len(sys.argv) > 2 else "unknown"

    if not os.path.exists(file_path):
        print(f"[错误] 文件不存在: {file_path}")
        return 1

    with open(file_path, "r", encoding="utf-8") as f:
        raw = f.read()

    source_file = os.path.basename(file_path)
    n = project_service.import_document(source_file, version, raw, allow_system=True)
    print(f"[完成] 导入 {n} 个分片")
    return 0


if __name__ == "__main__":
    exit(main())