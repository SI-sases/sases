from pathlib import Path

content = """# SASES 决策记录

## 2026-11-15 · post-scan-clean 基线
- 起点：f1d0bb8（d68b409 + API 胶囊恢复）
- 动作：幽灵依赖扫描 P0=0 / P1=0，清 7 条缝合遗留 P0
  - 3 个根目录孤儿文件：debug_service.py / export_service.py / group_service.py
  - 3 处相对导入层数错：cross_account_delivery.py:120/175 + executor_callback.py:6
  - 1 处 runs 路径错：from .runs -> from ..supervisor.runs
- 清理 12 个缝合期临时脚本（check_broken.py + scripts/fix_*.py 等）
- 远程覆盖：origin/main 的 12 个二次基建 commit（v0.51.0-all-green）已 force push 丢弃
- 找回入口：git reflog 或 tag v0.51.0-all-green
- 服务器同步：Node-A / Node-B 已 scp 传 2 个修好的文件 + rm 3 个孤儿 + restart
- 回滚命令：git checkout post-scan-clean -- <file>
"""

Path("docs/DECISIONS.md").write_text(content, encoding="utf-8")
print("写入完成:", Path("docs/DECISIONS.md").stat().st_size, "bytes")
