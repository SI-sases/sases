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
- 修复：绝对不要用 PowerShell -replace 改含中文的代码文件。用 Python 脚本（显式 encoding='utf-8'）或 file_patch 工具