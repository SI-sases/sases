# -*- coding: utf-8 -*-
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
  r"^core/.*\.py$",
  r"^harness_modules/.*\.py$",
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
      lines = text.split("\n")
      text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
  try:
      result = json.loads(text)
      return result if isinstance(result, list) else []
  except Exception:
      # 兜底：正则提取第一个 [...]
      m = re.search(r"\[.*\]", text, re.DOTALL)
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
          user=f"触发原因：{trigger_reason}\n请输出测试步骤 JSON。",
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


# ============================================================
# P1-0c 新增：同步执行测试步骤（供 executor_callback 调用）
# ============================================================
async def execute_test_steps_sync(test_steps):
    """同步执行测试步骤，返回结果列表

    支持：command / verify_syntax / run_python / file_read
    """
    import subprocess as _sp
    results = []

    for step in (test_steps or [])[:3]:  # 最多 3 步
        _type = step.get("type", "")
        _params = step.get("params", {}) or {}
        _step_no = step.get("step", len(results) + 1)

        try:
            if _type == "command":
                _cmd = _params.get("command", "")
                if not _cmd:
                    results.append({
                        "step": _step_no, "type": _type,
                        "status": "skipped", "output": "空命令",
                    })
                    continue
                _r = _sp.run(_cmd, shell=True, capture_output=True,
                             text=True, timeout=60, encoding="utf-8",
                             errors="replace")
                results.append({
                    "step": _step_no, "type": _type,
                    "status": "success" if _r.returncode == 0 else "failed",
                    "output": ((_r.stdout or "") + (_r.stderr or ""))[:500],
                })
            else:
                # verify_syntax / run_python / file_read
                from ...harness_runtime import invoke_tool
                _tool_result = await invoke_tool(_type, _params)
                if hasattr(_tool_result, "success"):
                    _ok = _tool_result.success
                    _out = str(getattr(_tool_result, "output", ""))[:500]
                elif isinstance(_tool_result, dict):
                    _ok = _tool_result.get("success") or _tool_result.get("syntax_ok")
                    _out = str(_tool_result)[:500]
                else:
                    _ok = False
                    _out = str(_tool_result)[:500]
                results.append({
                    "step": _step_no, "type": _type,
                    "status": "success" if _ok else "failed",
                    "output": _out,
                })
        except Exception as _e:
            results.append({
                "step": _step_no, "type": _type,
                "status": "failed",
                "output": f"异常: {type(_e).__name__}: {_e}"[:500],
            })

    return results
