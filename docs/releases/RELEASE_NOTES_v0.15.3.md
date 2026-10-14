\# SASES v0.15.3 Release Notes



\*\*Release Date:\*\* 2026-09-18

\*\*Previous Version:\*\* v0.15.2



\## Highlights



Executor is now integrated into the backend process. Users no longer need to start `executor\_v2.py` manually.



This release consolidates v0.15.1 (memory integration), v0.15.2 (draft mode + web\_fetch), and v0.15.3 (backend executor) into a single version.



\## v0.15.1 — Memory Integration



\- Commander reads `task\_result` and `failure\_pattern` memories separately

\- Reviewer writes failure memories on retry

\- Recalled memory capped at 120 chars



\## v0.15.2 — Draft Mode + Web Fetch



\- `草稿：` prefix triggers draft mode

\- Frontend renders editable draft editor

\- `web\_fetch` Harness tool for fetching web pages

\- Intent recognition: URL pattern detection

\- `AUTO\_GENERATE\_HARNESS = False` — disabled auto-generation of auto\_\* modules



\## v0.15.3 — Backend Executor



\- New `core/services/executor\_service.py`

\- New table `swarm\_pending\_tasks` for task persistence

\- `bootstrap.py` starts background executor task

\- Task auto-recovery on backend restart

\- Global concurrency limit (3 parallel tasks)

\- Any conversation in `free` mode triggers auto-execution



\## Architecture



&#x20;   Backend (app\_full.py)

&#x20;     ├── API routes

&#x20;     ├── Background executor (async task)

&#x20;     │     Scans swarm\_pending\_tasks every 3 seconds

&#x20;     │     Executes commands / harness tools

&#x20;     │     Reports via swarm\_service.handle\_step\_done

&#x20;     └── Auto-recovers unfinished tasks on restart



\## Security



| Check | Rule |

|-------|------|

| Whitelist | 17 read-only commands |

| Dangerous chars | `\& < > ^ % ; \\` $ \\n \\r` |

| Timeout | 30 seconds |

| Output limit | 2000 chars |



\## Testing



&#x20;   \[MSG\_DEBUG] content='列出 core 目录下的文件' | mode='free'

&#x20;   \[swarm] 检索到 2 条成功经验

&#x20;   \[MSG\_DEBUG] plan\_result={'status': 'planned', ...}

&#x20;   \[executor] ▶ 开始执行任务 t\_1789660577486

&#x20;   \[executor]   结果: success (64ms)

&#x20;   \[swarm] step 1 审核: pass |

&#x20;   \[swarm] 成功记忆已写入

&#x20;   \[executor] ✓ 任务 t\_1789660577486 处理完毕



\## Migration Notes



\- `executor\_v2.py` is deprecated. Manual startup no longer needed.

\- Users only need to configure agents in "模型管理".

\- Backend automatically matches commander/executor by agent names.



\## Known Limitations



1\. Backend crash mid-command may re-execute the task from start

2\. No conversation-level lock (parallel tasks in same conversation may interleave)

3\. `if` commands still forbidden in commander prompt

