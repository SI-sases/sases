# SASES v0.14.1 Release Notes

**Release Date:** 2026-09-16
**Previous Version:** v0.14.0-milestone2

## Highlights

This release introduces **natural-language swarm execution** — users can now trigger multi-agent task execution by simply typing a task in the chat box. No prefix, no mode switching, no manual agent selection required.

## New Features

### 1. Natural-Language Intent Detection

- New module: `core/services/intent_service.py`
- Two-layer detection: rule-based filter + LLM judge for the middle zone
- Automatically distinguishes "chat" from "task" without user prefixes
- Works in both `normal` and `free` modes

### 2. Backend Swarm Commander

- New module: `core/services/swarm_service.py`
- Auto-selects commander and executor agents from the user's agent pool
- Named agents (`指挥官`, `执行者`) are matched by keyword
- Falls back to positional selection (first agent = commander, second = executor)
- Single-agent accounts are supported (same agent plays both roles)

### 3. Cancel & Feedback Buttons

- After a task is triggered, two inline buttons appear for 10 seconds:
  - `⏹ 取消执行` — cancel a running task
  - `❌ 这不是任务` — mark a false positive (intent misclassification)
- False positives are logged to `intent_feedback` table for future rule tuning

### 4. `/swarm/plan`, `/swarm/cancel`, `/swarm/feedback` Endpoints

- `POST /swarm/plan` — plan a task (auto-selects agents if not provided)
- `POST /swarm/cancel` — cancel a pending task
- `POST /swarm/feedback` — record a false-positive feedback

## Protocol

Messages use internal prefixes that are hidden from the user flow:

| Prefix | Purpose |
|--------|---------|
| `[TASK]:` | Commander dispatches task to executor |
| `[STEP_DONE]:` | Executor reports step completion |
| `[SUMMARY]:` | Commander summarizes the result |

## Files Changed

| File | Change |
|------|--------|
| `core/services/intent_service.py` | NEW — intent detection |
| `core/services/swarm_service.py` | NEW — commander orchestration |
| `core/services/message_service.py` | MODIFIED — dispatch to swarm on task detection |
| `core/api_routes/swarm_routes.py` | NEW — swarm API endpoints |
| `static/modules/chat.js` | MODIFIED — cancel & feedback buttons |
| `executor_v2.py` | NEW — external executor daemon |
| `test_swarm.py` | NEW — manual test script |
| `test_intent.py` | NEW — intent test script |

## How to Test

1. Start backend:
   ```bash
   python -m uvicorn app_full:app --port 8001
Start executor in another terminal:

bash
python executor_v2.py <username> <password> <conversation_id> <commander_id> <executor_id>
In the browser, open a conversation and type:

text
列出当前目录
Expect:

AI reply: "已启动执行，请稍候…"

Two buttons appear below

Executor runs dir and reports back

AI reply: "[SUMMARY]: ..."

Breaking Changes
None. All previous modes (normal, free, swarm) continue to work.

Known Limitations
Intent detection still has false positives for questions like "怎么查看当前目录" (classified as task, but LLM refuses to plan). These are now flagged via the ❌ 这不是任务 button.

The --reload flag must be avoided in production because harness module generation triggers frequent restarts.