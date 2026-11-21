### 工具层：invoke_tool 的 success 有两层语义
- 第一层：handler 有没有抛异常（调用成功）
- 第二层：run() 返回的 result.success（业务成功）
- 修前只看第一层，导致所有"业务失败"被当成功
- 修后两层都看，任何工具返回 {'success': False} 都会被正确上报
- 影响：file_replace_range、verify_patch、verify_syntax、run_python 等所有返回 success 字段的工具



\## 2026-11-08



\### 坑 1：服务器工作区的行尾符污染

\- 现象：git diff 显示 5000 行改动，实际只有 263 行真改动

\- 根因：服务器 core.autocrlf 未设置，工作区 CRLF，仓库 LF

\- 修复：`git diff --ignore-cr-at-eol --stat` 看真改动；`git stash push -u` 后再 pull



\### 坑 2：core/db.py 手工建表未入代码

\- 现象：本地有 sync\_received 表，香港没有

\- 根因：P1-5 时 AI 直接在数据库跑 CREATE TABLE，没写进 db.py

\- 修复：把 CREATE TABLE 加进 init\_db()，push 后跑 init\_db() 补齐



\### 坑 3：bootstrap.py shutdown 引用未定义变量

\- 现象：kill -9 或 restart 时 NameError: summary\_task not defined

\- 根因：575 行用 \_background\_tasks.append 建任务，626 行引用 summary\_task 变量（从未定义）

\- 修复：626-635 改为 for \_t in \_background\_tasks: \_t.cancel()



### 坑 4：init_db() 不调用迁移，新环境缺字段
- 现象：新环境 init_db() 建 67 张基础表，缺 HLC 字段（shard_key/hlc_ts/origin_node）、transactions P1-4 字段、outbox 索引
- 根因：migrations.py 的 v1-v5 和 migrate_hlc_groundwork.py 是独立脚本，init_db() 从不调用
- 修复：db.py init_db() 末尾加两段幂等调用（apply_migrations + apply_hlc_groundwork）
- 教训：所有"加字段/加表"的迁移必须挂到 init_db()，不能只做独立脚本



### 坑 6：PowerShell -replace 处理含中文的 UTF-8 文件导致乱码
- 现象：执行 PowerShell 的 -replace 替换 chat_ui.js 内容后，所有中文变成乱码（如 '我' 变成 '鎴?'），且吞掉单引号引发 SyntaxError
- 根因：Windows PowerShell 5.1 的 Set-Content 默认使用系统 ANSI 编码（中文环境为 GBK），读写 UTF-8 文件时破坏中文字符
- 修复：绝对不要用 PowerShell -replace 改含中文的代码文件。用 Python 脚本（显式 encoding='utf-8'）或 run_python 工具


## safety_memory 直接 SQL 插入不生成 embedding
- 现象：recall 召回不到，`length(embedding)` 为 NULL
- 根因：embedding 由 memory_service.remember() 生成，SQL 直插绕过
- 规避：写入用 remember() API，或插入后跑 backfill_embeddings
- 兜底：bootstrap.py 定时任务（待实施）

## 降权 SQL 必须加 memory_type 过滤
- 错误写法：UPDATE safety_memory SET importance=0.1 WHERE content LIKE '%xxx%'
- 后果：会把新任务的 task_context 也降权（id=93 被误伤）
- 正确写法：UPDATE ... WHERE memory_type='file_patch_pattern' AND content LIKE '%xxx%'


## patch.py 维护策略
- 短补丁（≤30 行）进 patch.py，方便重放
- 长补丁（>30 行）直接在源码改，git commit 里体现
- 补丁稳定 3 个月后合并回源码，从 patch.py 删除
- 目标：patch.py 保持在 200-500 行内，不是无限膨胀


# SASES 常见坑点清单

## 一、工具层

### 1.1 file_patch old_snippet 分支崩溃
- 现象：`UnboundLocalError: cannot access local variable 'new_content'`
- 触发：传 `old_snippet` + `new_snippet` + `expected_count`
- 根因：`_mode_snippet` 分支里 `new_content` 变量未赋值
- 规避：**优先 run_python 字符串替换**，或 file_patch 的 `anchor_pattern` 模式
- 状态：目录已从三者可见范围移除（改名 `_disabled_file_patch`），prompts.py 已清

### 1.2 run_python 不能做的事
- 禁止 `import subprocess / socket / ctypes / multiprocessing / signal`
- 禁止 `import py_compile / compileall`
- 禁止启动外部进程
- 适合：字符串处理、文件读写（走 `write_file` / `open`，有路径白名单）、简单计算
- **需要跑外部脚本时**：三者指令写 `type=command`，写 `python scripts/xxx.py`；或用户 CMD 直接执行

### 1.3 三者按行号打补丁会越改越乱
- 现象：连续 3 次重拆，缩进错误从 line 305 → 304 → 306 反复挪动
- 根因：三者按"锚点行位置"逐行插入，每次改 1 行后行号变了，下次对不上
- 规避：**整函数替换**，或**精确字符串匹配替换**，不要按行号逐行插入

### 1.4 grep_code 扫到副本目录
- 现象：搜索 `harness_reload` 出来 `build_portable/...` 副本，噪音大
- 根因：`SKIP_DIRS` 漏了 `build_portable`、`python312`、`dist`、`release`、`logs`
- 规避：`SKIP_DIRS` 已扩展（patch.py 的 `grep_skip_dirs`）
- 遗留：`decider.py.broken_20261101` 这类 `.broken_` 备份没跳过，`SKIP_NAME_MARKERS` 里待加

### 1.5 直达通道会劫持"明确指定工具"的指令
- 现象：发 `调用 harness 工具（module_id=run_python）`，直达理解成 `file_read + grep`
- 根因：`_should_try_direct` 只看"有文件路径"，不看"已指定工具"
- 规避：`try_direct` 开头加 `_explicit_tool_call` 判断（patch.py 的 `direct_no_hijack`）

### 1.6 直达空消息
- 现象：`messages` 表出现 `content=""` 的 assistant 记录，聊天窗口空白
- 根因：`try_direct` 返回空字符串，`send.py` 照样 INSERT
- 规避：直达返回空时不写消息，或写"未找到匹配内容"（待修）

## 二、记忆库

### 2.1 直接 SQL 插 safety_memory 不生成 embedding
- 现象：`recall` 召回不到，`length(embedding)` 为 NULL
- 根因：embedding 由 `memory_service.remember()` 生成，SQL 直插绕过
- 规避：写入用 `remember()` API，或插入后跑 `backfill_embeddings`
- **兜底方案**：`bootstrap.py` 定时任务每 30 分钟跑一次 `backfill_embeddings`（见第二部分）

### 2.2 降权 SQL 必须加 memory_type 过滤
- 错误写法：`UPDATE safety_memory SET importance=0.1 WHERE content LIKE '%xxx%'`
- 后果：会把新任务的 `task_context` 也降权（id=93 被误伤）
- 正确写法：`UPDATE ... WHERE memory_type='xxx_type' AND content LIKE '%xxx%'`

### 2.3 语义检索对短 query 命中率低
- 现象：所有 93 条记忆，query"当前任务是什么"，最高 sim=0.527，全部 < 0.55 阈值
- 根因：BGE-small-zh 对短 query（7 个字）vs 长 content（几十字）天然相似度低
- **不要降全局阈值**：降到 0.45 会召回一堆历史任务，污染上下文
- 规避：**关键上下文走 recall_by_type 确定性注入**，不走语义检索

### 2.4 task_context 必须走 recall_by_type
- 位置：`context_service.build_enriched_prompt`
- 逻辑：`memory_service.recall_by_type(user_id, 'task_context', top_k=2)` 精确按类型查，不用相似度
- 效果：只要用户有 task_context，必注入，不受模型能力影响
- 对所有用户生效，按 user_id 隔离

## 三、上下文注入

### 3.1 项目库高分命中跳过 build_enriched_prompt
- 现象：`[message] 项目库高分命中 0.676` 后直接拼 project_text，task_context 完全没注入
- 根因：`send.py` 1212-1215 行高分分支没调 `build_enriched_prompt`
- 规避：patch.py 的 `send_proj_high_ctx`，高分时也走 `build_enriched_prompt`

### 3.2 会话历史 10 条盖过 task_context
- 现象：新会话能答对，旧会话答"149 个文件"（旧任务）
- 根因：`build_enriched_prompt` 里历史 10 条紧跟 task_context，LLM 看到旧任务优先相信
- 规避：有 task_context 时历史只取 2 条（patch.py 的 `ctx_task_context` 的 `_hist_limit`）

### 3.3 _is_sases_chat 只认 'sases' 名字
- 现象：用户配置的"调度"名字不含 `sases`，判 False，走"仅注入历史"分支，不读项目库
- 规避：patch.py 的 `send_is_sases_chat`，改成 `True`，所有智能体都注入上下文

## 四、数据一致性

### 4.1 init_db 从来不是唯一真相来源
- 问题：表、字段、索引分散在 CREATE TABLE、migrations.py、手工 SQL 四个地方
- 后果：新环境部署时缺表缺字段，启动后才爆
- 规避：所有"加表/加字段"必须挂到 `init_db()` 末尾调 migrations
- 现状：`init_db` 已集成 `apply_migrations` + `apply_hlc_groundwork`

### 4.2 数据库字段必须 PRAGMA 确认
- 教训：AI 说"已加字段"的次数很多，实际没加的次数也很多
- 规避：每次改表后跑 `PRAGMA table_info(表名)` 确认

## 五、工具链与流程

### 5.1 patch.py 维护策略
- 短补丁（≤30 行）进 `scripts/patch.py`，方便重放
- 长补丁（>30 行）直接在源码改，git commit 里体现
- 补丁稳定 3 个月后合并回源码，从 patch.py 删除
- 目标：patch.py 保持在 200-500 行内，不是无限膨胀
- 新机器部署：`python scripts/patch.py --all` 一键恢复

### 5.2 CMD 转义
- 多行 `python -c` 在 CMD 下会截断
- `$`、`{}`、反引号在 CMD 下会转义
- 复杂逻辑：写脚本文件，`python scripts/xxx.py` 执行
- 简单查询：单行 `python -c "..."`，用 `chr()` 拼特殊字符

### 5.3 修改 core/ 必须重启
- 改 `core/` 下 `.py` 文件 → 必须 `Ctrl+C` + 重启
- 改 `static/` 下 `.js` / `.css` → 硬刷新（Ctrl+Shift+F5）即可
- 改 `harness_modules/` → 调 `harness_reload` 工具即可，不用重启

### 5.4 三者重拆上限
- 连续 3 次重拆未修好 → 停手
- 每次重拆烧 2 积分，改错方向损失更大
- 停手后：用户手动看日志 + 写脚本修 + 走 CMD 执行

## 六、验证与审计

### 6.1 verify_patch 的 all_checks_passed 审核员不检查
- 现象：`verify_patch` 返回 `success: true` 但 `all_checks_passed: false`，审核员判 `pass`
- 根因：`reviewer.py` 只看 `success`，不看 `all_checks_passed`
- 影响：补丁没落地被当成成功
- 待修：`reviewer.py` 加 `all_checks_passed` 判断

### 6.2 三者"假成功"
- 已加防护：`file_patch` 写后读回校验、`run_python` 备份
- 仍需注意：AI 说"已改"，必须 `grep_code` 或 `file_read` 物理验证

## 七、直达通道

### 7.1 直达回显的两种返回格式
- `file_read` 不带 `grep` → 返回 `{"content": "..."}`，能回显
- `file_read` 带 `grep` → 返回 `{"matches": [...]}`，`execute_direct` 取 `content` 拿不到，返回空
- 待修：`execute_direct` 加 `matches` 格式化分支

### 5.5 patch.py 字符串锚点必须带缩进
- 现象：`IndentationError: unexpected indent`，插入的代码变成 0 缩进
- 根因：`anchor_b = '_background_tasks.append(...)'` 没带 4 空格，`str.replace` 只替换子串，替换后新加行没缩进
- 规避：**函数体内的锚点必须带前导空格**，`anchor = '    _background_tasks...'` 而不是 `'_background_tasks...'`
- 教训：`str.replace` 是子串替换，不是行级替换。锚点必须包含足够的上下文（含缩进）才能精确

### 5.7 project_docs 检索 query 要含核心关键词
- 现象：query = "SASES 当前状态" 命中 0 条；query = "SASES" 命中 3 条
- 根因：BGE 对短 query + 长内容的相似度敏感，泛化词（"当前状态"）会稀释语义
- 规避：
  - 检索 query 必须含 1-2 个具体关键词（项目名、模块名、技术词）
  - 不要用纯泛化词（"当前状态"、"最近怎样"、"东西在哪"）
  - 0 命中时先换 query 试，不要立刻怀疑数据
- 阈值 0.48 是合理的：`SASES` 能命中说明数据没问题

### 工具层：file_replace_range 替换单行不保留缩进
- 现象：`file_replace_range(start_line=10, end_line=10, new_content='api2')` 把原行 `            raise Exception(...)` 换成 0 缩进的 `api2`，破坏语法
- 根因：替换时直接 `new_lines = before + [new_content] + after`，没取原行缩进
- 修复：取原行前导空格拼到 new_content 前
- 教训：行级替换工具必须处理缩进

### 工具层：SELF_PROTECTED 必须包含工具自己
- 原 file_patch 有自我保护，file_patch 废弃后 file_replace_range 继承了位置但没继承保护
- 修复：SELF_PROTECTED 换成 file_replace_range 的 main.py + manifest.json
- 教训：工具自我保护是防止 AI 改坏工具本身，每个写入类工具都该有

### 异步审核：reviewer_deep 不能直接 await invoke_tool
- 现象：`TypeError: object ToolInvokeResponse can't be used in 'await' expression`
- 根因：`invoke_tool` 是同步函数，返回 ToolInvokeResponse，不能 await
- 修复：`await asyncio.to_thread(invoke_tool, ...)`
- 教训：同步函数包 async 上下文必须走 to_thread

### 工具层：harness 模块改了必须 reload
- 现象：改了 `harness_modules/xxx/main.py`，但 invoke_tool 跑的还是旧代码
- 根因：`harness_runtime` 单例缓存模块对象，文件改了不重启不 reload
- 规避：改 harness 工具后必须 `get_runtime().reload_modules()` 或重启服务
- 教训：**harness 热更新是显式动作，不是自动**。三者调 `harness_reload` 工具也是同理

### 工具层：invoke_tool 忽略 run() 返回的 success: False
- 现象：工具 run() 返回 `{'success': False, 'error': '...'}`，但 `ToolInvokeResponse.success` 是 True
- 根因：`invoke_tool` 只看 handler 有没有抛异常，不看 result 的 success 字段
- 影响：所有工具的“业务失败”被当成功，上层判断全部错
- 修复：handler 返回后检查 result.get('success') is False，是则 ToolInvokeResponse.success=False
- 教训：**工具返回值两层语义**：`success`（调用成功）vs `result.success`（业务成功）。两层都要检查

### 工具层：SELF_PROTECTED 生效依赖重启，reload_modules 不彻底
- 现象：改 `harness_modules/xxx/main.py` 后 `reload_modules()`，但 invoke_tool 还是跑旧代码
- 根因：`del sys.modules[module_name]` 只删顶层模块，跨模块 import 引用仍缓存旧代码
- 规避：改 harness 工具后必须重启服务，不能只 reload
- 长期：`_load_module_function` 前先清所有 `harness_*` 开头的 sys.modules 键