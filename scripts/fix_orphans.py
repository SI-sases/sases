"""一次性修复 7 条 P0"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent

def fix_cross_account():
    f = ROOT / "core/services/cross_account_delivery.py"
    text = f.read_text(encoding="utf-8")

    # 修 1：120 行附近的 from .. import intent_service → from . import intent_service
    old1 = "from .. import intent_service"
    new1 = "from . import intent_service"
    if old1 in text:
        text = text.replace(old1, new1)
        print(f"[fix] cross_account_delivery: {old1} → {new1}")
    else:
        print(f"[skip] cross_account_delivery: 未找到 '{old1}'")

    # 修 2：175 行附近的 from ... import config → from .. import config
    old2 = "from ... import config"
    new2 = "from .. import config"
    if old2 in text:
        text = text.replace(old2, new2)
        print(f"[fix] cross_account_delivery: {old2} → {new2}")
    else:
        print(f"[skip] cross_account_delivery: 未找到 '{old2}'")

    f.write_text(text, encoding="utf-8")

def fix_executor_callback():
    f = ROOT / "core/services/swarm/executor_callback.py"
    text = f.read_text(encoding="utf-8")
    old = "from .runs import get_run, finish_run"
    new = "from ..supervisor.runs import get_run, finish_run"
    if old in text:
        text = text.replace(old, new)
        print(f"[fix] executor_callback: {old} → {new}")
    else:
        print(f"[skip] executor_callback: 未找到 '{old}'")
    f.write_text(text, encoding="utf-8")

def remove_orphans():
    orphans = [
        "core/debug_service.py",
        "core/export_service.py",
        "core/group_service.py",
    ]
    for path in orphans:
        r = subprocess.run(["git", "rm", "-f", path], cwd=ROOT,
                           capture_output=True, text=True)
        if r.returncode == 0:
            print(f"[git rm] {path}")
        else:
            print(f"[git rm 失败] {path}: {r.stderr.strip()}")

if __name__ == "__main__":
    print("=== 1. 修 cross_account_delivery.py ===")
    fix_cross_account()
    print("\n=== 2. 修 executor_callback.py ===")
    fix_executor_callback()
    print("\n=== 3. 删除 3 个孤儿文件 ===")
    remove_orphans()
    print("\n=== 完成 ===")
