\# SASES v0.15.2 Release Notes



\*\*Release Date:\*\* 2026-09-17

\*\*Previous Version:\*\* v0.15.1



\## Highlights



This release adds three major capabilities:



1\. \*\*Draft mode\*\* — users can review and edit tasks before execution

2\. \*\*Web fetch\*\* — the swarm can now retrieve web pages via a built-in Harness tool

3\. \*\*Auto-harness disabled\*\* — stopped generating low-value `auto\_\*` modules



\## New Features



\### 1. Draft Mode (User-in-the-Loop)



Users can prefix a message with `草稿：`, `草稿:`, `编辑：`, or `编辑:` to enter draft mode:



&#x20;   Input: 草稿：列出 core 目录下的文件

&#x20;   → Commander plans

&#x20;   → \[TASK\_DRAFT]: sent

&#x20;   → Frontend renders editable card

&#x20;   → User edits commands or descriptions

&#x20;   → User clicks "✅ 确认执行"

&#x20;   → POST /swarm/confirm → \[TASK]: dispatched



The frontend draft editor allows editing each step's command inline before confirming.



\*\*Default behavior:\*\* Direct execution (no confirmation required). Draft mode is opt-in via prefix.



\### 2. Web Fetch Harness Tool



New built-in Harness module `web\_fetch`:



| Feature | Value |

|---------|-------|

| Input | URL |

| Output | Plain text (HTML stripped, first 2000 chars) |

| Timeout | 10 seconds |

| Size limit | 100 KB |

| Security | Private IP addresses blocked |



Commander now knows when to use it:



&#x20;   Input: 抓取 https://example.com 的内容

&#x20;   → Commander plans: \[{"step":1,"type":"harness","module\_id":"web\_fetch","params":{"url":"..."}}]

&#x20;   → Executor calls /harness/execute

&#x20;   → Returns page text



\### 3. Auto-Harness Generation Disabled



Previously, every task generated a new `auto\_\*` Harness module (e.g., `auto\_33\_dir`, `auto\_40\_findstr\_n\_i\_funct`). These had no encapsulation value and triggered repeated uvicorn reloads.



\*\*Change:\*\* `AUTO\_GENERATE\_HARNESS = False` in `work\_service.py`.



Manual Harness registration remains available for valuable tools like `web\_fetch`.



\### 4. Intent Recognition: URL Detection



Added `URL\_PATTERN` to `intent\_service.py`:



&#x20;   r'https?://\[^\\s]+'



Any input containing a URL is now classified as a task, even without task verbs.



Extended `TASK\_VERBS` with: 抓取、获取、爬取、拉取、请求、访问.



Extended `TASK\_NOUNS` with: 网页、链接、网址、内容、页面、站点、网站.



\## Bug Fixes



| Bug | Fix |

|-----|-----|

| `plan\_task() got an unexpected keyword argument 'require\_confirmation'` | Added `require\_confirmation` parameter |

| `\[TASK\_DRAFT]:` polluted conversation history | Filtered in `\_get\_conversation\_history` |



\## Files Changed



| File | Change |

|------|--------|

| `core/services/swarm\_service.py` | + draft mode, + confirm/reject functions, + web\_fetch prompt |

| `core/services/message\_service.py` | + draft prefix detection |

| `core/services/intent\_service.py` | + URL pattern, + extended verbs/nouns |

| `core/services/work\_service.py` | + `AUTO\_GENERATE\_HARNESS = False` |

| `core/api\_routes/swarm\_routes.py` | + `/swarm/confirm`, + `/swarm/reject` |

| `executor\_v2.py` | + harness step support (`type: "harness"`) |

| `static/modules/chat.js` | + `showDraftEditor` function |

| `harness\_modules/web\_fetch/manifest.json` | NEW |

| `harness\_modules/web\_fetch/main.py` | NEW |

| `clean\_auto\_harness.py` | NEW — cleanup utility |



\## Testing Results



\### Draft Mode



&#x20;   \[MSG\_DEBUG] content='草稿：列出 core 目录下的文件' | mode='free'

&#x20;   \[MSG\_DEBUG] 检测到草稿前缀，切换为草稿模式

&#x20;   \[swarm] 草稿模式：任务 t\_xxx 已生成草稿，等待用户确认

&#x20;   \[swarm] 用户已编辑草稿 t\_xxx，新步骤数: 1

&#x20;   \[swarm] 草稿 t\_xxx 已确认，下发执行



\### Web Fetch



&#x20;   \[执行者] 收到任务 t\_xxx，共 1 步

&#x20;     步骤 1: 抓取 https://example.com 的网页内容

&#x20;       \[Harness] web\_fetch({'url': 'https://example.com'})

&#x20;       结果: success (936ms)

&#x20;       输出: Example Domain This domain is for use in illustrative examples...



\## Known Limitations



1\. \*\*Draft mode not persisted\*\* — if backend restarts before confirmation, the draft is lost

2\. \*\*Web fetch supports only GET\*\* — no POST, no auth headers

3\. \*\*No domain whitelist\*\* — any public URL allowed (private IPs blocked)

4\. \*\*`if` command still forbidden\*\* — commander must use simpler commands

