# -*- coding: utf-8 -*-
"""P1-0 深度审核基础设施搭建脚本"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ============================================================
# 文件 1：docs/knowledge/TEST_TOOL_CATALOG.md
# ============================================================
CATALOG_CONTENT = """# 可用于测试的工具清单

> 审核员出题时的参考手册。触发 L2 深度审核时，审核员 LLM 会读取本清单。

## 语法测试

### verify_syntax
- **参数**：`file_path`（相对路径）
- **返回值**：`{syntax_ok: bool, errors: [...]}`
- **适用**：任何 `.py` / `.js` 改动后必跑
- **示例**：
{"type": "verify_syntax", "params": {"file_path": "core/services/swarm/reviewer_deep.py"}}

text

## 功能测试

### run_python
- **参数**：`code`（Python 代码字符串，≤5000 字符）
- **返回值**：执行结果或异常
- **适用**：验证具体函数的输入输出
- **示例**：
{"type": "run_python", "params": {"code": "from core.utils.helper import add; assert add(1,2)==3"}}

text

## 输出验证

### file_read
- **参数**：`file_path` + `offset`（可选）+ `max_lines`（可选）
- **返回值**：文件内容
- **适用**：验证改动后的具体行
- **示例**：
{"type": "file_read", "params": {"file_path": "core/xxx.py", "offset": 10, "max_lines": 5}}

text

## 命令测试

### command
- **参数**：`command`（单行命令字符串）
- **返回值**：`{status: success|failed, output, exit_code}`
- **适用**：跑已有测试文件、跑 linter
- **示例**：
{"type": "command", "params": {"command": "python -m pytest tests/test_xxx.py -v"}}

text

## 出题原则（审核员 LLM 必读）

1. **改了 .py → 必跑 verify_syntax**
2. **改了具体函数 → 必跑一个 assert 验证该函数**
3. **有对应测试文件 → 必跑该测试文件**
4. **无法验证的改动（如改注释）→ 输出空数组 `[]`**
5. **最多 3 步**：超过 3 步说明改动太大，应退回指挥员重拆
6. **不要假设环境里有不存在的测试文件**
"""
catalog_path = ROOT / "docs" / "knowledge" / "TEST_TOOL_CATALOG.md"
catalog_path.parent.mkdir(parents=True, exist_ok=True)
catalog_path.write_text(CATALOG_CONTENT, encoding="utf-8")
print(f"[OK] 写入 {catalog_path.relative_to(ROOT)} ({catalog_path.stat().st_size} bytes)")

# ============================================================
# 文件 2：core/services/swarm/reviewer_deep.py
# ============================================================
REVIEWER_DEEP_CONTENT = '''# -*- coding: utf-8 -*-
"""L2 深度审核：审核员出题 → 执行员答题 → 汇报调度员

设计原则：
- L1（现有 review_step）一行不改，本模块只在 L1 判 pass 之后按需触发
- 同一任务最多升级 2 次，防死循环
- 测试结果不直接决定 retry，而是汇报给调度员综合判断
"""
import json
import re
import time
from typing import Optional

# ============================================================
# 触发判断
# ============================================================

# 触发关键词（任务描述含这些词 → 触发 L2）
TEST_KEYWORDS = ["测试", "验证", "跑通", "端到端", "检查", "assert"]

# 高风险文件模式（改这些文件 → 触发 L2）
RISKY_PATTERNS = [
  r"^core/.*\\.py$",
  r"^harness_modules/.*\\.py$",
]

# 每个 task 的深度审核次数（内存计数，服务重启清零）
_DEEP_REVIEW_COUNTS: dict = {}

MAX_DEEP_REVIEW_PER_TASK = 2


def should_deep_review(task: dict, step_result: dict) -> tuple:
  """判断是否触发 L2 深度审核

  Returns:
      (should_trigger: bool, reason: str)
  """
  task_id = task.get("task_id", "")

  # 防死循环：同一任务最多升级 2 次
  count = _DEEP_REVIEW_COUNTS.get(task_id, 0)
  if count >= MAX_DEEP_REVIEW_PER_TASK:
      return False, f"已升级 {count} 次，不再深度审核"

  if step_result.get("status") != "success":
      return False, "执行失败，走现有 retry"

  user_text = task.get("user_text", "") or task.get("goal", "")

  # 条件 1：任务描述含测试关键词
  for kw in TEST_KEYWORDS:
      if kw in user_text:
          return True, f"任务含关键词「{kw}」"

  # 条件 2：改的是高风险文件
  steps = task.get("steps", [])
  for step in steps:
      params = step.get("params", {}) or {}
      file_path = params.get("file_path", "")
      for pattern in RISKY_PATTERNS:
          if re.match(pattern, file_path):
              return True, f"改的是高风险文件「{file_path}」"

  # 条件 3：file_patch 无实际 diff（L1 有轻微怀疑）
  if step_result.get("module_id") == "file_patch":
      if not step_result.get("diff_bytes", 0):
          return True, "file_patch 无实际改动"

  return False, "不需要深度审核"


def mark_deep_review_used(task_id: str):
  """标记一次深度审核已使用"""
  _DEEP_REVIEW_COUNTS[task_id] = _DEEP_REVIEW_COUNTS.get(task_id, 0) + 1


def reset_deep_review_count(task_id: str):
  """任务完成/放弃时清空计数"""
  _DEEP_REVIEW_COUNTS.pop(task_id, None)


# ============================================================
# 审核员出题
# ============================================================

def _parse_json_array(text: str) -> list:
  """从 LLM 输出中提取 JSON 数组（容错）"""
  text = (text or "").strip()
  # 去 markdown 包裹
  if text.startswith("```"):
      lines = text.split("\\n")
      text = "\\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
  try:
      result = json.loads(text)
      return result if isinstance(result, list) else []
  except Exception:
      # 兜底：正则提取第一个 [...]
      m = re.search(r"\\[.*\\]", text, re.DOTALL)
      if m:
          try:
              result = json.loads(m.group())
              return result if isinstance(result, list) else []
          except Exception:
              pass
  return []


async def generate_test_steps(task: dict, step_result: dict, trigger_reason: str) -> list:
  """审核员出题：调 LLM 生成测试步骤（最多 3 步）

  Returns:
      测试步骤列表，失败返回 []
  """
  try:
      # 延迟 import 避免循环依赖
      from .prompts import REVIEWER_DEEP_PROMPT
      from ..llm_client import call_llm  # 复用现有 LLM 客户端

      goal = task.get("user_text", "") or task.get("goal", "")
      step_desc = json.dumps(
          {
              "module_id": step_result.get("module_id"),
              "params": step_result.get("params"),
              "output": (step_result.get("output") or "")[:500],
              "status": step_result.get("status"),
          },
          ensure_ascii=False,
      )

      system_prompt = REVIEWER_DEEP_PROMPT.format(goal=goal, step_result=step_desc)

      resp = await call_llm(
          system_prompt=system_prompt,
          user=f"触发原因：{trigger_reason}\\n请输出测试步骤 JSON。",
          max_tokens=800,
          temperature=0.1,
      )

      steps = _parse_json_array(resp)
      # 严格限制最多 3 步
      return steps[:3]

  except Exception as e:
      print(f"[reviewer-deep] 出题失败: {e}")
      return []


# ============================================================
# 派发测试任务给执行员
# ============================================================

MSG_TEST_TASK = "[TEST_TASK]:"
MSG_TEST_RESULT = "[TEST_RESULT]:"


async def dispatch_test_task(task: dict, test_steps: list) -> Optional[str]:
  """把测试步骤派给执行员

  Returns:
      test_task_id，失败返回 None
  """
  if not test_steps:
      return None

  try:
      from ..db import db_cursor

      test_task_id = f"test_{task.get('task_id')}_{int(time.time())}"

      payload = {
          "test_task_id": test_task_id,
          "parent_task_id": task.get("task_id"),
          "steps": test_steps,
      }

      # 写入 swarm_pending_tasks（复用现有队列）
      with db_cursor(commit=True) as cur:
          cur.execute(
              """INSERT INTO swarm_pending_tasks
                 (task_id, conversation_id, status, task_type, steps_json, created_at)
                 VALUES (?, ?, ?, ?, ?, datetime('now'))""",
              (
                  test_task_id,
                  task.get("conversation_id"),
                  "pending",
                  "test",
                  json.dumps(test_steps),
              ),
          )

      print(f"[reviewer-deep] 派发测试任务: {test_task_id} ({len(test_steps)} 步)")
      return test_task_id

  except Exception as e:
      print(f"[reviewer-deep] 派发失败: {e}")
      return None
'''

reviewer_path = ROOT / "core" / "services" / "swarm" / "reviewer_deep.py"
reviewer_path.write_text(REVIEWER_DEEP_CONTENT, encoding="utf-8")
print(f"[OK] 写入 {reviewer_path.relative_to(ROOT)} ({reviewer_path.stat().st_size} bytes)")

print("\\n=== P1-0 第 2 步完成 ===")
print("下一步：手工在 prompts.py 末尾追加 REVIEWER_DEEP_PROMPT")
print("      并在 executor_callback.py 插入 3 行触发判断")
