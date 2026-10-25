# scripts/fix_prompt.py
"""一次性脚本：更新 COMMANDER_SYSTEM_PROMPT 中 file_patch 的权限描述。"""
import os
import shutil
from datetime import datetime

TARGET = "core/services/swarm_service.py"

REPLACEMENTS = [
    (
        "- file_patch：修改 static/ 目录下的前端文件。支持两种模式：",
        "- file_patch：修改项目文件（允许目录：static/ / core/ / scripts/ / docs/）。支持两种模式："
    ),
    (
        "  f) 不要修改 core/ 目录、.env、users.db。file_patch 会拒绝。",
        "  f) 允许修改：static/ / core/ / scripts/ / docs/ 下的文件。\n"
        "     禁止修改：users.db / .env / *.key / *.bin / *.pem / *.crt。\n"
        "     修改 core/ 下的文件后，用户需要重启服务才能生效，请在 description 中提醒。"
    ),
]


def main():
    if not os.path.exists(TARGET):
        print(f"[错误] 找不到 {TARGET}")
        return 1

    os.makedirs(".backups", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f".backups/swarm_service.py.{ts}.bak"
    shutil.copy2(TARGET, backup)
    print(f"[备份] {backup}")

    with open(TARGET, "r", encoding="utf-8") as f:
        content = f.read()

    changed = 0
    for i, (old, new) in enumerate(REPLACEMENTS, 1):
        if old in content:
            content = content.replace(old, new)
            changed += 1
            print(f"[OK] 替换第 {i} 处")
        else:
            print(f"[跳过] 第 {i} 处未找到（可能已更新）")

    if changed == 0:
        print("\n没有任何修改。请手动检查 core/services/swarm_service.py 的 file_patch 段落。")
        return 0

    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n[完成] 共替换 {changed} 处。请重启服务使提示词生效。")
    return 0


if __name__ == "__main__":
    exit(main())
