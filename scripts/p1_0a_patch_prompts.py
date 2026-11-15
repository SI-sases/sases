# -*- coding: utf-8 -*-
"""P1-0-a-1：给两个 prompt 加"降级硬规则"（幂等）"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "core/services/swarm/prompts.py"

# 加给 REPLAN 的规则（插在【重拆策略】之前）
REPLAN_INSERT = """【同类错误 2 次立即换方法（硬规则）】
- 如果 file_patch 报错包含"超过 20 行"、"超过20行"、"单次替换超过"：
  → 禁止第 2 次再用 file_patch，立即改用 {"type":"harness","module_id":"run_python","params":{"code":"..."}}
  → run_python 里用 open().read() + 字符串替换 + open().write() 完成整文件重写
- 如果 file_patch 报错包含"原片段未找到"、"anchor 未找到"：
  → 第 1 次用 file_read 精确确认原文
  → 第 2 次仍找不到，立即改用 run_python 整文件重写
- 如果同一个工具连续 2 次报同类错误：立即换工具，严禁第 3 次用同一个工具

"""

# 加给 COMMANDER 的规则（插在【工具优先级】或开头附近）
COMMANDER_INSERT = """
【新建/大文件规则（避免撞 file_patch 20 行限制）】
- 新建文件：文件内容 >20 行的，用 {"type":"harness","module_id":"run_python","params":{"code":"..."}} 写，禁止用 file_patch 一次性创建
- 整文件覆盖：任何超过 20 行的整文件覆盖，用 run_python，禁止用 file_patch
- file_patch 只用于：单行替换、≤20 行的精确片段替换、锚点插入
- 如果 file_patch 报"超过 20 行"，立即改用 run_python，禁止第 2 次用 file_patch 做同一件事

"""


def patch_prompt_file():
    content = PROMPTS.read_text(encoding="utf-8")
    original = content

    # ---- 给 REPLAN 加规则 ----
    if "同类错误 2 次立即换方法" in content:
        print("[SKIP] REPLAN 规则已存在")
    else:
        # 找 REPLAN 的【重拆策略】
        anchor = "【重拆策略】"
        if anchor in content:
            content = content.replace(anchor, REPLAN_INSERT + anchor, 1)
            print("[OK] REPLAN 规则已插入")
        else:
            print("[WARN] 找不到【重拆策略】锚点，改用结尾插入")
            content = content + "\n" + REPLAN_INSERT
            print("[OK] REPLAN 规则已追加到末尾")

    # ---- 给 COMMANDER 加规则 ----
    if "新建/大文件规则（避免撞 file_patch 20 行限制）" in content:
        print("[SKIP] COMMANDER 规则已存在")
    else:
        # 在 COMMANDER_SYSTEM_PROMPT 的规则 1 之后插入
        # 找 COMMANDER_SYSTEM_PROMPT = """你是 SASES 指挥官... 后面的位置
        commander_start = content.find("COMMANDER_SYSTEM_PROMPT")
        if commander_start == -1:
            print("[ERROR] 找不到 COMMANDER_SYSTEM_PROMPT")
            return False

        # 找 COMMANDER 定义里的第一个【工具故障必须降级】或类似段落
        # 用规则 1 之后插入
        rule1_end = content.find("\n", content.find("COMMANDER_SYSTEM_PROMPT")) + 100
        # 在 COMMANDER_SYSTEM_PROMPT 之后的前 2000 字符内找第一个空行
        insert_pos = content.find("\n\n", commander_start)
        if insert_pos == -1 or insert_pos > commander_start + 2000:
            # 兜底：在 COMMANDER_SYSTEM_PROMPT 之后紧接插入
            insert_pos = content.find("\n", commander_start) + 1

        content = content[:insert_pos] + "\n" + COMMANDER_INSERT + content[insert_pos:]
        print("[OK] COMMANDER 规则已插入")

    if content == original:
        print("[SKIP] 无改动")
        return True

    PROMPTS.write_text(content, encoding="utf-8")
    print(f"[OK] prompts.py 已更新，新大小 {PROMPTS.stat().st_size} bytes")
    return True


if __name__ == "__main__":
    patch_prompt_file()
