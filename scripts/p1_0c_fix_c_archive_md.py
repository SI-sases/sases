# -*- coding: utf-8 -*-
"""修复 C：归档历史快照 + 列出待确认文件"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ARCHIVE = DOCS / "archive"
ARCHIVE.mkdir(exist_ok=True)

# 要归档的文件（历史快照类，保留但移出 docs 根目录）
TO_ARCHIVE = [
    "schema_diff.md",   # 79KB 历史 schema 对比
]

today = datetime.datetime.now().strftime("%Y%m%d")

for fname in TO_ARCHIVE:
    src = DOCS / fname
    if not src.exists():
        print(f"[SKIP] {fname} 不存在")
        continue
    dst = ARCHIVE / f"{today}_{fname}"
    shutil.move(str(src), str(dst))
    print(f"[OK] {fname} → archive/{dst.name}")

# 列出 100-500 字节的小文件
print("\n[100-500 字节的小文件，请确认是否保留]")
for md in DOCS.rglob("*.md"):
    try:
        size = md.stat().st_size
    except Exception:
        continue
    if 100 <= size < 500:
        print(f"  {md.relative_to(DOCS)} ({size}B)")
        try:
            content = md.read_text(encoding="utf-8", errors="replace")
            # 打印前 3 行
            for line in content.splitlines()[:3]:
                print(f"    | {line[:80]}")
        except Exception:
            pass

print("\n=== 修复 C 完成 ===")
print("提示：小文件不自动删，人工确认后再手动删")
