# -*- coding: utf-8 -*-
"""P1-0：定位 call_llm 和 db_cursor 的真实位置"""
from pathlib import Path

print("=== 搜索 call_llm / _call_llm 定义 ===")
for p in Path("core").rglob("*.py"):
    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for i, line in enumerate(content.splitlines(), 1):
        s = line.strip()
        if s.startswith("def call_llm") or s.startswith("async def call_llm") \
           or s.startswith("def _call_llm") or s.startswith("async def _call_llm"):
            print(f"{p}:{i}: {s}")

print("=== 搜索 db_cursor 定义 ===")
for p in Path("core").rglob("*.py"):
    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for i, line in enumerate(content.splitlines(), 1):
        s = line.strip()
        if s.startswith("def db_cursor") or s.startswith("async def db_cursor") \
           or s.startswith("def _db_cursor") or s.startswith("async def _db_cursor"):
            print(f"{p}:{i}: {s}")

print("=== 搜索 call_llm 调用点 ===")
for p in Path(".").rglob("*.py"):
    if any(part in ("venv312", "python312", ".git", "__pycache__") for part in p.parts):
        continue
    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for i, line in enumerate(content.splitlines(), 1):
        if "call_llm(" in line and "def " not in line:
            print(f"{p}:{i}: {line.strip()}")

print("=== 搜索 db_cursor 调用点 ===")
for p in Path(".").rglob("*.py"):
    if any(part in ("venv312", "python312", ".git", "__pycache__") for part in p.parts):
        continue
    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for i, line in enumerate(content.splitlines(), 1):
        if "db_cursor(" in line and "def " not in line:
            print(f"{p}:{i}: {line.strip()}")
