# -*- coding: utf-8 -*-
"""修复 decider.py：白名单加 file_write（幂等）"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEC = ROOT / "core/services/supervisor/decider.py"
content = DEC.read_text(encoding="utf-8")

old_line = """        _has_success_patch = any(r.get('command') == 'file_patch' and r.get('status') == 'success' for r in _res)
        _has_success_python = any(r.get('command') == 'run_python' and r.get('status') == 'success' for r in _res)"""

new_line = """        _WRITE_TOOLS = ('file_patch', 'run_python', 'file_write')
        _has_success_patch = any(
            (r.get('command') in _WRITE_TOOLS or r.get('module_id') in _WRITE_TOOLS)
            and r.get('status') == 'success' for r in _res
        )
        _has_success_python = _has_success_patch  # 合并判断，向后兼容"""

if old_line in content:
    content = content.replace(old_line, new_line, 1)
    print("[OK] 白名单已加 file_write")
elif "_WRITE_TOOLS" in content:
    print("[SKIP] 白名单已修复")
else:
    print("[ERROR] 找不到原文，手工检查")
    exit(1)

DEC.write_text(content, encoding="utf-8")
print(f"[OK] decider.py 已更新，{DEC.stat().st_size} bytes")
