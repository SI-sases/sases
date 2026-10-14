\# SASES v0.15.1 Release Notes



\*\*Release Date:\*\* 2026-09-17

\*\*Previous Version:\*\* v0.15.0



\## Highlights



This release connects the three-agent architecture to the \*\*semantic memory system\*\*, making the system learn from every successful and failed task.



The commander now reads relevant memories before planning, and the reviewer writes failure patterns. The system gets smarter with each task.



\## New Features



\### 1. Commander Reads Memory



Before planning, the commander queries the memory system with the user input and retrieves the top-2 most relevant memories.



Memory context is injected into the planning prompt as `【相关历史经验】`, capped at 120 characters per entry.



\### 2. Commander Writes Success Memory



When a task completes successfully, a `task\_result` memory is written:



&#x20;   task\_result

&#x20;   任务「列出 core 目录下的文件」成功完成。

&#x20;   使用命令：

&#x20;     1. dir core



This memory becomes searchable for future similar tasks.



\### 3. Reviewer Writes Failure Memory



When a step fails, a `failure\_pattern` memory is written:



&#x20;   failure\_pattern

&#x20;   命令「dir /s /b nonexistent\_file\_xyz.js」执行失败。

&#x20;   失败原因：命令状态: failed



Repeated failures are deduplicated by semantic similarity.



\### 4. Skipped Status for Dependent Steps



When a step fails, subsequent steps that reference it via `{{stepN}}` placeholders are now marked as `skipped` instead of executing with un-substituted placeholders.



\### 5. Placeholder Detection



Before executing a command, the executor checks whether any `{{stepN}}` or `{stepN}` placeholders remain. If so, the step is skipped with a clear reason.



\## Bug Fixes



| Bug | Fix |

|-----|-----|

| Recall returned 0 results | Threshold 0.65 → 0.55 (tuned for BGE Chinese) |

| Memory text polluted prompt format | Truncate to 120 chars, remove newlines |

| LLM returned non-JSON on complex prompts | Strengthened format constraints in prompt |

| Commander generated `if` commands | Added "禁止使用 if 条件语句" to system prompt |

| `\_cosine\_sim` shape mismatch | Added `.flatten()` on both sides |



\## Testing



Full end-to-end test with `查看 nonexistent\_file\_xyz.js 里的函数名`:



&#x20;   \[swarm] 检索到 2 条相关记忆

&#x20;   \[swarm] step 1 审核: retry | 命令状态: failed

&#x20;   \[swarm] 失败记忆已写入

&#x20;   \[swarm] step 2 审核: retry | 跳过：依赖步骤失败

&#x20;   \[swarm] 发现 2 个失败步骤，触发重拆 (第 1 次)

&#x20;   \[swarm] 重拆成功，新步骤数: 4

&#x20;   \[swarm] step 1 审核: retry | 命令状态: failed

&#x20;   \[swarm] step 2 审核: retry | 命令状态: failed

&#x20;   \[swarm] step 3 审核: pass |

&#x20;   \[swarm] step 4 审核: pass |

&#x20;   \[swarm] 发现 2 个失败步骤，触发重拆 (第 2 次)

&#x20;   \[swarm] 所有失败均为不可恢复错误，跳过重拆



Memory dedup also verified:



&#x20;   \[memory] 语义重复 (sim=0.951)，跳过写入



\## Files Changed



| File | Change |

|------|--------|

| `core/services/swarm\_service.py` | + memory read in plan\_task, + success/failure memory write, + skipped handling, + prompt updates |

| `core/services/memory\_service.py` | Threshold tuning, flatten fixes |

| `executor\_v2.py` | + placeholder check before execution |



\## Known Limitations



1\. \*\*No memory type filtering in recall\*\* — returns all types mixed

2\. \*\*Memory prompt length cap 120 chars\*\* — long memories truncated

3\. \*\*Retry cap is 2\*\* — complex tasks may need more attempts

4\. \*\*`if` command forbidden\*\* — commander must use simpler command sequences

