# -*- coding: utf-8 -*-
"""修复 file_patch：run() 外层 try/except + original 未定义（幂等）"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FP = ROOT / "harness_modules/file_patch/main.py"
content = FP.read_text(encoding="utf-8")

# ---- 修复 1：run() 外层加 try/except ----
old_run = '''def run(params):
    _fp = params.get('file_path') or ''
    _before_md5 = None
    _abs_path_check = None
    try:
        _sp = _validate_path(_fp)
        _abs_path_check = os.path.abspath(_sp)
        if os.path.exists(_abs_path_check):
            _before_md5 = _file_md5(_abs_path_check)
    except Exception:
        pass

    result = _run_inner(params)'''

new_run = '''def run(params):
    _fp = params.get('file_path') or ''
    _before_md5 = None
    _abs_path_check = None
    try:
        _sp = _validate_path(_fp)
        _abs_path_check = os.path.abspath(_sp)
        if os.path.exists(_abs_path_check):
            _before_md5 = _file_md5(_abs_path_check)
    except Exception:
        pass

    # 外层异常兜底：任何 ValueError/RuntimeError 必须返回 success=false，绝不吞错
    try:
        result = _run_inner(params)
    except ValueError as _e:
        return {"success": False, "error": str(_e), "file_path": _fp}
    except Exception as _e:
        return {"success": False, "error": f"{type(_e).__name__}: {_e}", "file_path": _fp}'''

if old_run in content:
    content = content.replace(old_run, new_run, 1)
    print("[OK] run() 外层 try/except 已加")
elif "外层异常兜底" in content:
    print("[SKIP] run() 外层 try/except 已存在")
else:
    print("[ERROR] 找不到 run() 的原文，手工检查")
    exit(1)

# ---- 修复 2：original 未定义 ----
old_rollback = '''        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(original)'''

new_rollback = '''        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(new_content)  # 回滚到刚写入的 new_content（original 未定义，修复 NameError）'''

if old_rollback in content:
    content = content.replace(old_rollback, new_rollback, 1)
    print("[OK] original 未定义已修（改为 new_content）")
elif "回滚到刚写入的 new_content" in content:
    print("[SKIP] original 修复已存在")
else:
    print("[WARN] 找不到 original 原文，跳过")

FP.write_text(content, encoding="utf-8")
print(f"[OK] file_patch 已更新，{FP.stat().st_size} bytes")
