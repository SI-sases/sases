\# SASES v0.15.0 Release Notes



\*\*Release Date:\*\* 2026-09-17

\*\*Previous Version:\*\* v0.14.2



\## Highlights



This release introduces the \*\*Reviewer\*\* (审核员) as the third pillar of the three-agent swarm architecture, adds \*\*security hardening\*\* to the executor, and \*\*rebuilds the memory system\*\* with semantic retrieval and deduplication.



The three-agent architecture is now complete:



| Role | Responsibility |

|------|---------------|

| \*\*Commander\*\* (指挥员) | Reads conversation history, plans commands, re-plans on failure |

| \*\*Executor\*\* (执行员) | Executes commands with security whitelist, reports results |

| \*\*Reviewer\*\* (审核员) | Judges each step, triggers retry or skip on failure |



\---



\## New Features



\### 1. Reviewer Mechanism



The reviewer inspects every `\[STEP\_DONE]` message and classifies it as:



| Verdict | Condition |

|---------|-----------|

| \*\*pass\*\* | Status is success, no error keywords, non-empty output for read commands |

| \*\*retry\*\* | Status is failed/timeout/error, error keywords present, empty output for read commands |



Error keywords include: `FINDSTR: 无法打开`, `系统找不到指定的路径`, `Access is denied`, `不是内部或外部命令`, and more.



\### 2. Re-planning on Failure



When failures are detected, the commander is invoked again with:



\- Original user task

\- Completed steps and their results

\- Failed steps and failure reasons



The commander produces a new plan using `{{stepN}}` placeholders to reference previous outputs. The new task is dispatched as a `\[RETRY\_TASK]:` message.



\*\*Retry cap:\*\* 2 attempts, then forced summary.



\### 3. Irrecoverable Error Detection



If all failures share keywords like `找不到文件`, `文件不存在`, `拒绝访问`, the system skips re-planning and directly summarizes. This avoids useless LLM calls.



\### 4. Executor Security Hardening



\*\*Command Whitelist (17 commands):\*\*

dir, ls, tree, type, cat, head, tail,

findstr, find, grep, where,

echo, pwd, cd, whoami, hostname, wc



text



\*\*Dangerous Character Blacklist (10):\*\*

\& < > ^ % ; ` $ \\n \\r



text



Commands with pipes (`|`) are allowed but each segment is checked separately.



\*\*Timeout:\*\* 30 seconds per command.



\*\*Output Truncation:\*\* 2000 characters.



\### 5. Review Log Storage



New table `swarm\_reviews`:



| Field | Description |

|-------|-------------|

| task\_id | Task identifier |

| conversation\_id | Conversation |

| step\_id | Step number |

| command | Executed command |

| exec\_status | success/failed/blocked/timeout/error |

| review\_result | pass/retry |

| review\_reason | Reason for verdict |

| output\_preview | First 200 chars of output |



New API: `GET /swarm/reviews?limit=50\&task\_id=xxx`



\### 6. Memory System Rebuild



\*\*New fields in `safety\_memory` table:\*\*



| Field | Purpose |

|-------|---------|

| task\_id | Link memory to source task |

| embedding | BGE-small-zh embedding (BLOB, 512 dims) |

| content\_hash | SHA256 for exact dedup |



\*\*Semantic Retrieval:\*\*



\- Uses local BGE-small-zh model (no external API)

\- Cosine similarity against stored embeddings

\- Threshold: 0.65 (tuned for BGE Chinese distribution)



\*\*Double-layer Deduplication:\*\*



| Layer | Method | Threshold |

|-------|--------|-----------|

| 1 | SHA256 hash | Exact match |

| 2 | Semantic similarity | 0.95 |



Duplicate memories update `created\_at` instead of inserting new rows.



\*\*Migration script:\*\* `migrate\_memory\_embeddings.py` backfills embeddings for existing memories.



\---



\## Bug Fixes



| Bug | Fix |

|-----|-----|

| Chinese output garbled (GBK vs UTF-8) | Added `smart\_decode` with multi-encoding fallback |

| `{{stepN}}` substitution from failed step | Only successful steps store outputs for substitution |

| `\_cosine\_sim` shape mismatch | Added `flatten()` to handle 2D arrays |



\---



\## Files Changed



| File | Change |

|------|--------|

| `core/services/swarm\_service.py` | + Reviewer, + retry, + review log, + irrecoverable check |

| `executor\_v2.py` | + whitelist, + dangerous chars, + timeout, + truncation, + smart\_decode |

| `core/services/memory\_service.py` | Rewritten: + embedding, + semantic search, + dedup |

| `core/api\_routes/memory\_routes.py` | + task\_id parameter |

| `core/db.py` | + task\_id/embedding/content\_hash columns, + indexes |

| `migrate\_memory\_embeddings.py` | NEW — migration script |

| `test\_memory.py` | NEW — test script |

| `test\_security.py` | NEW — security test |

| `RELEASE\_NOTES\_v0.15.0.md` | NEW — this file |



\---



\## Testing Results



\### Reviewer

\[swarm] step 1 审核: pass |

\[swarm] step 1 审核: retry | 命令状态: failed

\[swarm] 发现 2 个失败步骤，触发重拆 (第 1 次)

\[swarm] 所有失败均为不可恢复错误，跳过重拆



text



\### Security

⛔ 命令被拒绝: 命令不在白名单: copy



text



\### Memory

测试 1：写入记忆 memory\_id = 53

测试 2：hash 去重 ✅ 去重成功

测试 3：语义去重 (0.977) ✅ 去重成功

测试 4：语义检索 (0.7018) ✅ 返回 1 条



text



\### Review Log

{'id': 1, 'task\_id': 't\_xxx', 'step\_id': 1, 'command': 'dir core',

'exec\_status': 'success', 'review\_result': 'pass', 'review\_reason': ''}



text



\---



\## Architecture Snapshot

用户输入（自然语言）

↓

意图识别 → is\_task?

↓

指挥员读会话历史 → 拆解

↓

\[TASK]: task\_id, steps

↓

执行员（白名单 + 超时 + 截断）

↓

\[STEP\_DONE]: 每步结果

↓

审核员判定

├─ pass → 继续

└─ retry → 触发 \[RETRY\_TASK]: → 指挥员重拆

↓

\[SUMMARY]: 最终汇总

↓

审核日志 → swarm\_reviews

记忆入库 → safety\_memory（embedding + dedup）



text



\---



\## Known Limitations



1\. \*\*Retry cap is 2\*\* — complex tasks may need more attempts

2\. \*\*Reviewer rules are hardcoded\*\* — new error patterns require code changes

3\. \*\*Memory type restricted\*\* — currently only `task\_result` and `periodic\_summary` in use

4\. \*\*Agent auto-selection by keyword\*\* — Chinese names like "指挥官/执行者" are matched; other names fall back to position

5\. \*\*No concurrency control\*\* — simultaneous tasks in one conversation are serialized but may interleave

