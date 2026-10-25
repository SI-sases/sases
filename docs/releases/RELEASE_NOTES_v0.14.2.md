\# SASES v0.14.2 Release Notes



\*\*Release Date:\*\* 2026-09-16

\*\*Previous Version:\*\* v0.14.1



\## Highlights



This release fixes a \*\*HTML injection vulnerability\*\* in the chat UI, adds \*\*cross-step placeholder substitution\*\* in the executor, and gives the commander access to \*\*conversation history\*\* for better context-aware planning.



\## Security Fix



\### HTML Injection in Chat UI



\*\*Issue:\*\* `chat\_ui.js` concatenated message content directly into `innerHTML`. When `findstr` or other commands returned text containing HTML tags (e.g., `<div>`, `<span>`), the browser parsed them as markup, breaking the layout and potentially allowing XSS.



\*\*Fix:\*\* Added `escapeHtml()` function and applied it to all three `innerHTML` concatenation points in `chat\_ui.js`.



\## New Features



\### 1. Cross-Step Placeholder Substitution



The commander can now reference previous step outputs using `{{stepN}}` placeholders:



```json

\[

&#x20; {"step": 1, "description": "Locate file", "command": "dir /s /b discover.js"},

&#x20; {"step": 2, "description": "Search in file", "command": "findstr /n \\"function\\" {{step1}}"}

]

The executor substitutes {{step1}} with the first non-empty line of step 1's output before execution.



2\. Conversation History for Commander

The commander now reads the last 10 messages of the conversation before planning. This enables context-aware planning:



User: "列出当前目录" → commander learns the working directory



User: "也看看 core 目录里有哪些文件" → commander knows the project root, plans dir core directly



Improvements

3\. Removed Duplicate Work Log

The executor's report\_work() call was duplicating information already present in \[STEP\_DONE]: messages. Commented out to reduce message clutter.



4\. UTF-8 Safe Command Execution

The executor now uses encoding="utf-8", errors="replace" when running subprocess, preventing UnicodeDecodeError crashes when reading UTF-8 files on GBK-locale Windows systems.



Files Changed

File	Change

static/modules/chat\_ui.js	Added escapeHtml, applied to 3 innerHTML points

core/services/swarm\_service.py	Added \_get\_conversation\_history, updated prompt with {{stepN}} syntax

executor\_v2.py	Added substitute\_placeholders, UTF-8 subprocess, removed duplicate report

core/services/intent\_service.py	Extended TASK\_NOUNS, added FILE\_EXT\_PATTERN

clean\_last.py	NEW — utility for cleaning last N messages

query\_last\_msgs.py	NEW — utility for viewing recent messages

Known Limitations

Placeholder substitution uses only the first line of a step's output. Multi-line path scenarios are not yet supported.



Conversation history is capped at 10 messages. Long conversations may lose early context.

