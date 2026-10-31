# SASES 状态快照



> 最后更新：2026-09-26

> 维护方式：三者完成任务后自动追加"最近修复"；你手动整理其他章节



---



## 一、环境



- 虚拟环境：`venv312`

- 启动命令：`python scripts/run_forever.py`

- 端口：`8001`

- 测试账号：

&#x20; - `test / 123456`（管理员，ID=1）

&#x20; - `222222 / 123456`

&#x20; - `666666 / 123456`

- 数据库：`users.db`（SQLite）



---



## 二、已完成能力



- 种子架构闭环（发芽-生长-验证-回溯）

- 三角色体系：调度员 / 指挥官 / 执行员 / 审核员

- 续跑机制（`running_resumed`，重启后跳过 restart_pending 防死循环）

- wrapper 自动重启（端口清理 + 杀进程树）

- 知识库导入权限保护（`allow_system=True` 才能写 user_id=0）

- `execution_notes` 跨用户隔离

- cleanup 扫描器（测试残留检测，白名单跳过自身）

- 权限保护：仅 SASES 助手（`sases_assistant*` / `sases_api_*`）能触发知识库导入

- 执行笔记隔离（`_ISOLATE_EXECUTION_NOTE = True`，不污染个人项目库）



---



## 三、已知问题



- **续跑空转**：`resume` 时 task_summarizer 判断保守，导致已完成的 run 仍做无用探测（烧 4-8 积分，不紧急）

- **`task_summarizer` 假阴性**：日志出现"剩余/请继续"就判 goal_achieved=false，可能误判



---



## 四、待办



- [ ] `project_service.py` 加 `*1/*2/*3` 编号

- [ ] `chat_menu.js` 多选文件 + 粘贴截图

- [ ] `chat_ui.js` 多附件预览（微信样式平齐）

- [ ] `chat.css` 样式微调

- [ ] `docs/SASES_STATE.md` 后台自动同步任务

- [ ] 用户级状态接入 UI 知识库



---



## 五、关键文件路径



| 模块 | 路径 |

|------|------|

| 调度员 | `core/services/supervisor_service.py` |

| 指挥官 + 审核员 | `core/services/swarm_service.py` |

| 执行员 | `core/services/executor_service.py` |

| 消息分流 | `core/services/message_service.py` |

| 项目库 | `core/services/project_service.py` |

| 清理 | `core/services/cleanup_service.py` |

| wrapper | `scripts/run_forever.py` |

| 三角色 prompt | `core/services/swarm_service.py` 顶部 |

| 数据库表定义 | `core/db.py` |

| 路由注册 | `core/bootstrap.py` |

| Harness 工具 | `harness_modules/` |



---



## 六、常用调试命令



```bash

# 启动服务

python scripts/run_forever.py



# 查看积分

python -c "from core.services import credit_service; print(credit_service.get_balance(1))"



# 查看最近 run

python -c "import sqlite3; conn=sqlite3.connect('users.db'); conn.row_factory=sqlite3.Row; cur=conn.cursor(); cur.execute('SELECT id,status,current_round,goal FROM supervisor_runs ORDER BY id DESC LIMIT 5'); [print(dict(r)) for r in cur.fetchall()]"



# 查看测试残留

python -c "from core.services import cleanup_service; r=cleanup_service.scan_test_marks(); print('发现:', r['count'])"



# 手动触发 cleanup

python -c "from core.services import cleanup_service; print(cleanup_service.cleanup_all())"

## 七、最近修复

（下方由 state_service 每 24 小时自动追加）

在 core/s

在 core/services/mess

在 core/services/agen

在 core/se

在 core/services/messa

在 core/serv

在 core

"""批量启动 hive

蜂群积分模拟脚本，模拟 3 个独

改动 A（core 脚本 sc

ol

old_snippet

old_snippet:

目标文件：

调用 1：
  module_id: file_copy
  params: {src: "

调用 1：src="core/api_routes/hive_routes.py", dst="D

调用 1：src="core/services/group_service.py", d

old_snippet:
        cur.e

调用 1：src="core/services/swarm_se

old_sni

调用 1：src="core/db.py", dst="D:/sases1/core/

import sqlite3
L=[]
for n,p in [('A','C:/Users/xiaomai/sas

调用 1：src="core/services/group_se

import sqlite3
for n, p in [('A','C:/Users/xiaomai/sases/users

调用 1：src="core/api_routes/hive_routes.py", d

import asyncio
import websockets

async def

改动 B：core/bootstrap.py 注册 ws

调用 1：src="static/modules/group_chat

调用 1：src="core/services/execu

ol

调用 1：src="core/services/executor_service.py"

import sqlite3
L = []
for n, p in [('A','C:/Users/xiaomai/sase

调用 1：src="static/modules/ws_client.js", dst=

import asyncio
import websockets
import httpx
import json

asy

调用 1：src="core/api_routes/ws_routes.

o
  1. 不再无差别标记所有 running 为 interrupted
 

用 run_python 执行：

from core.services im

改动 1：在 _parse_plan 函数之后（约 830 行）加新函数
o

1. file_read 读 harness_modules/file_re

第 1 轮：用 file_read 的 grep 模式读 static/css/chat.css 中含"border-radius"和"pa

第 1 轮：用 read_file 的 grep 模式读出 chat.css 中所有 border

背景：

参考：现有"群公告编辑"页面的实现方式。
要求：
1. 点击"群聊名称"行 → 打开二级页面
2

背景：今天统计发现，调度员的 API 缓存命中率约 67-73%，明显偏低。
原因可能是动态内

【原理】
DeepSeek 按"前缀 token 段"匹配缓存。前缀一样，后面

现象：

现象：run_forever.py 运行一段时间后抛出 UnicodeEncodeErr

背景：今天三者对 run_forever.

【当前状态】
launcher/ 下已有：

【当前状态】
launcher/ui/main_window.py 里点"启动"时，直接启动新的 run_forever.

【现象】
在 sases/ 目录下跑 python launcher/launcher.py 报错：
Impo

原因

要

要求：

【当前状态】
launcher/ui/main_window.py 的 start() 方法：

[CONTENT]:
第一段：这是多段测试的第一个内容块。

[CONTENT

[CONTENT]:
# SASES 自愈评估指标

[CONTENT]:
# SASES 自愈评估指标

[CONTENT]:
# SASES 自愈评估指标

[CONTENT]:
第一段：这是多段测试的第一个内容块。

[CONTENT

[CONTENT]:
# SASES 自愈评估指标

[CONTENT]:
# SASES 自愈评估指标

[CONTENT]:
# SASES 自愈评估指标

[CONTENT]:
# SASES 自愈评估指标

[CONTENT]:
# SASES 自愈评估指标

---

第 1 段：
第一段：这是 v4 多段测试的第一个内容块。

---

第 2 段：

改动 1：在 group_chat.js 末尾补 openGroupSettings 的 window 挂载


参数：
  fil

问题：delete_block 现在用"从 start_pattern 往下找第一个 end_mar

删除 users.db 的第 1 行到第 2 行（start_pattern="sqlite", end_mar

问题描述：
delete_block 在删除多函数串联的代码时，会把"删除范围之后、紧邻的下一个函

背景：三个函数从第 409 行到第 575 行

[CONTENT]:
# 大文件拆分操作手册

背景：当前的拆分流程需要 7 个手工步骤（grep、切片、写新文件

严格按 docs/SPLIT_PLAYBOOK.md

[CONTENT]:
# 大文件拆分操作手册

第 1 步：用 file_patch 创建测试源文件
  file_path: "data/_test_split_

第 1 步：先 file_read 确认缩进
  file_path: "core

第 1 步：grep_code 

执行步骤：

第 1 步：gre

目标文件：core/api_routes/group_routes.py

问题：POST /{group_id}/red-packets/create 插入 group_messages 

第 1 步：用 run_python 修复 group_redpacket_ui.js
  代码：
    c = r

背景：拆分群红包时，拆出的新文件用了 api 但没带 import { api }，运行时崩溃

f

用 split_block 工具执行：
  source_file: "data/_test_spl

第 1 步：grep_code 确认边

直接执行，不要先探测边界（已知位置：103

第 1 步：grep_code 确认边

第 1 步

第 1 步：用 delete_block dry_run 读 group_chat.js 里的 openGroupRe

第 1 步：delete

第 1 步：用 delete_block dry_run 读 group_chat.js 里的 open

第 1 步：用 file_patch 在 data/_test_done.js 创建一个简单文件
  file_path:

第 1 步：用 file_patch 创建测试源文件 data/_test_prefix_src

约束：

约束：

1. 读取 static/modules/chat.js，找到 openChatWindow 的定义（大约 478 行

目标 1：读取 core/services/message/conversations.py，在 SELECT 语句中加上 c.is

1. 读取 core/services/swarm/

1. 读取 harness_modules/file_patch/main.py。
2

现象：会话列表的 DOM 上直接显示了 `data-is-friend="0

【任务 1：修改 messages.js 补全传参】
1. 读取 static/mod

1. 读取 core/services/swarm/prompts.py。
2

1. 检查后端的同意好友接口（POST /agents/friend-requests/accept）。
2. 使用

1. 读取 core/api_routes/agent_routes.py。
2. 将原来的

1. 读取 core/services/m

1. 读取 static/modules/ws_client.js。
2. 检查 WebSocket 实例是否挂

【第一步：删除旧代码】
1. 读取 c

1. 读取 static/modules/chat_ui.j

【任务1：修改 cross_acco

1. 读取 core/serv

1. 读取 static/modules/chat.js。
2

1. 读取 static/modules/chat_ui.js。
2. 使用 file_patch 精确片段模

1. 读取 core/services/message/send.py，按 Ctrl+F

1. 当前 static/modules/chat.js 已经被你

1. 读取 st

1. 读取 static/modules/

背景：group_messages 表已有 msg_type、at

第 1 点：定位 core/services/message/send.py 里 sender='user' 的 INSER

需要探测的点：

1. static/modules 里 go-register 的事件绑定在哪

修复 1：core/services/swarm

背景：
run 490 的日志显示"续

第 1 点：plan_task 返回"需要澄清"时的返回值形式

背景：L63 的 timedelta(min

背景：

第 1 点：get_active_run 完整实现

第 1 段：executor_callback.py 的 L250-310
code:
with open(

第 1 点：正常完成路径——task_summarizer 判定完成后走哪

背景：

背景：finish_run 推送

code:
import ast

# ========== 1

code:
print("=" * 30, "1. executor_callback.py

code:
import ast

p = "core/services/swarm/executor

code:
import ast

# ========== 1. prompts.py 

print("=== B-1: agent_routes.py friend-mode

print("=== B-1: chat.js L540-580 ===")
with

用 run_python 执行：
print("=== B-1: chat.js L478-

背景：刚才的 run 546 触发 plan_failed，但三者在第 1 轮报告说已经把 deliv

背景：A 和 B 两个账号互为好友，模式切换按钮已经工作（普通→自由切换成功），但发消息后对方收不到。日志显示 `is_ta

背景：
好友聊天的四种组合里，普通模式应该是"本人 ↔ 本人"，但当前 openChatWindow 

背景：建立好友关系时，agent_routes.py 硬编码了 f"与 

调用 ssh_exec，host=node-B，command 

调用 ssh_exec，host=node-B，command 为：
mkdir -p /etc/n

调用 ssh_exec，host=node-B，command 为：
apt-g

调用 ssh_exec，host=node-B，command 为：
ap

anchor_

第 1 步：用 file_patch create_if_missing 创建

调用 ssh_exec，host=node-B，command 为：
curl -k -s -m 5 h

调用 ssh_exec，host=node-A，

file_path 为 "laun

第 1 步：修复图标路径

code 为：
import subprocess
r = subprocess.run(["python", 

调用 harness 工具（type=command），command 为：
pytho

调用 harness 工具（type=command），command 为：
python s

先 file_re

old_snippet

用 command 执行：
python scripts/build_launcher_exe.py

执行完直接结

old_sni

第 1 步：用 file_patch 修改 scripts/build_l

第 1 步：左侧导航增加选项。
old_snip

第 1 

用 command 执行：
python scripts/build_launcher_exe.py

执行完直接结束，不要生成 find

用 file_patch 锚点模

第 1 步：用 file_patch cre

old_s

第 1 步：

old_snippet 为：

old_snippet 为：
    # #5 清锁（最先拦截，绕过所有锁检查）
    i

command 为：
python scripts/build_launcher_exe.py

执行完直接结束，不要生成 f


command 为：
python scripts/build_launcher_exe.py

执

先 file_

第 1 步：修复 core/bootstrap.py 的

找到 subprocess.run(["gi

找到判断 ret

anc

先 file_read st



先 file_read 读取 static

第 1 步：用 file_patch 找到 static/

第 1 步：用 grep_code 搜索 "关于 SASES"

第 1 步：用 file_patch 清理 static/mod

第 1 步：用 run_python 执行以下代码（修复 file_patch 

第 1 步：用 grep_code 搜索 "MAX_ROUND

【执行清单】
1. 用 file_patch 修改 static/mod

【现象】
1. 点击设置里的任意二级页面，返回时直接退回到了“我的”主界面，而不是“设置

【排查与修改】
第 1 步：用 grep_code 搜索 "supervis

用 run_python 执行以下代码：
code = '''
import os, 

【目标】
前端胶囊选择什么轮数，后端就执行多少轮；如果前端未传，后端降级使用 .env 中的默

用 file_patch 修改 core/services/swarm/prompts

【诊断结论】
1. 底层数据库存的字段叫 `max_rounds`，前端传的叫 `max_ste

【背景】
前端胶囊传递的 `max_steps`（如 8、15、-1）是“大

【现象】
在“我的”->“设置”中，点击“授粉计划”、“记忆管理”、“关于SASES”等选项进入二级页面后，点击左上角的返

【现象】
在“我的”->“设置”中，点击“授粉计划”或“关于SASES”进入二级页面后，点

在【执行铁律】最前面插入以下规

第 1 步：读取 static/modules/me_sett

【目标】
你刚才已经列出了所有行号，现在立刻调用 file_patch 或 run_py

【背景现象】
1. 点击设置里的二级页面返回，无法回到一级页面，甚至卡死。
2. 网页

执
- 2026-10-25: 排查并修复前端白屏问题。必须提供 file:line 和错误原因。

【背景】
刚才任务执行完成后，刷新网页出现白屏，前端静态资源可能加载失败或有语法错误。
- 2026-10-25: 纯只读排查。请把 executor_callback.py 中控制任务结束和续跑的真实代码原样打印出来。

第 1 步：用 file_read 读取 core/
- 2026-10-25: 先读取 core/services/supervisor/decider.py，找到里面名叫 _fake_words 的变量，把它改成 ['test']，并在最
- 2026-10-25: 先读取 core/services/supervisor/decider.py，然后在这个文件里找一个叫 "_is_fake" 的变量，把它的判断逻辑改回原来的
- 2026-10-25: 先读取 core/services/supervisor/decider.py，然后找到 _fake_words 变量，把它改成 ['test']
- 2026-10-25: 先读取 core/services/supervisor/decider.py，然后找到 `_fake_words` 变量，把它改成 `['test']`，并在
- 2026-10-25: 先读取 core/services/supervisor/decider.py，然后找到 _fake_words 变量，把它改成 ['test']，最后确认没有
- 2026-10-25: 用 file_patch 精确片段模式，精准切除 subpage.js 的坏代码。

old_snippet 为：
  window.__currentRetu
- 2026-10-25: 用 file_patch 精确片段模式，修改 contacts.js 中 API智能体的跳转参数。

old_snippet 为：
      else if 
- 2026-10-25: 用 file_patch 精确片段模式，给 me_models.js 的 openModelManagement 增加返回逻辑。

第 1 步：修改函数签名。
- 2026-10-25: 用 file_patch 精确片段模式，将 activateMainView 挂载到 window 上。

old_snippet 为：
function ac
- 2026-10-25: 用 file_patch 精确片段模式，给 subpage.js 里的返回键补上绑定，彻底解决无法返回的问题。

old_snippet 为：
  if (vi
- 2026-10-25: 用 file_patch 精确片段模式，单点修复 closeSubpage 函数。

old_snippet 为：
  const viewSubpage = 
- 2026-10-25: 用 file_patch 精确片段模式，修改联系人点击逻辑，实现微信级交互。

old_snippet 为：
    if (agentType === 'fr
- 2026-10-25: 一次 run_python 完成三件事：清信号、备份、覆盖。不许判断、不许犹豫、只调一次 run_python。

code 参数（逐字复制，不许改）：

im
- 2026-10-25: 用 run_python 执行以下代码（逐字复制，不许改），完成打包并验证。不要创建脚本文件，不要用 file_patch，只调一次 run_python。
- 2026-10-25: 修复服务重启时的无限死循环 Bug。

背景：
三者在完成任务修改 core/ 后，会触发 restart_pending 并写入 restart_signal
- 2026-10-25: 清理瘦客户端环境下的后台噪音日志，并增加静默机制。

背景：
瘦客户端（如广州机器）没有安装 Git，没有跑全量数据库迁移，也没有对等节点，但后台定时任务依然在
- 2026-10-25: 修复 core/services/swarm/prompts.py 的转义警告。

背景：
服务启动时报警告：prompts.py 第 108 行附近有 `Sy
- 2026-10-25: 用 run_python 执行以下打包代码，生成更新包。

code（逐字）：

import os, zipfile, ast
ROOT = r'C:\Use
- 2026-10-25: 用 run_python 强制修复两个源头文件，直接覆写。

把下面的代码作为 run_python 的 code 参数执行：

import os

# 1.
- 2026-10-25: 验证单任务 API 熔断机制。

要求：
1. grep_code 搜索 `budget_exceeded` 或 `credits_used` 或 `max_a
- 2026-10-25: 用 run_python 执行以下强制注入脚本，彻底锁死无限重启与无限重试。

把下面的代码作为 run_python 的 code 参数执行（只调一次 run
- 2026-10-25: 用 run_python 执行打包代码，生成最新更新包。

code（逐字）：
import os, zipfile, ast
ROOT = r'C:\User
- 2026-10-25: 用 run_python 执行以下脚本，强制修复 core/db.py 中遗漏的数据库迁移字段。

把下面的代码作为 run_python 的 code 参数执
- 2026-10-25: 用 run_python 执行打包代码，生成最新更新包。

code（逐字）：

import os, zipfile, ast
ROOT = r'C:\Use
- 2026-10-25: 用 run_python 执行以下修复脚本，解决编码报错并补齐加好友接口，跑完重新打包。

把下面的代码作为 run_python 的 code 参数执行（逐字
- 2026-10-25: 实现登录页显示“下载桌面版”按钮，登录成功后自动隐藏该按钮。

背景：
目前在登录页有“下载桌面版”按钮，但登录进入主界面后，这个按钮依然存在，影响界面美观，需
- 2026-10-30: 扫描 static/modules/ 下的 .js 文件和 static/ 目录下的 .html 文件，找出所有包含中文的行。必须先 grep_code 搜索。
- 2026-10-31: 任务：将 static/modules/contacts.js 中暴露给用户的硬编码中文，批量改成中英双语（例如 搜索 -> 搜索 / Search）。

要求






## 标准流程（已验证 3 次）

### 第

## 标准流程（已验证 3 次）

### 第
- 2026-10-18: 把 group_chat.js 里的群知识库三个函数迁出到新文件 group_knowledge_ui.js。

关键约束：每一步都要打印实际结果，确认正确后才

## 背景
自愈能力不能靠感

## 背景
自愈能力不能靠感

## 背景
自愈能力不能靠感

## 背景
自愈能力不能靠感

## 背景
自愈能力不能靠感

## 背景
自愈能力不能靠感
- 2026-10-16: 创建 docs/_test_special_chars.md，内容如下：

[CONTENT]:
# 特殊字符测试

## JSON 片段
{"key": "v

## 背景
自愈能力不能靠感
- 2026-10-16: 创建 docs/_test_special_chars.md，内容如下：

[CONTENT]:
# 特殊字符测试

## JSON 片段
{"key": "v

## 背景
自愈能力不能靠感
- 2026-10-16: 创建 docs/_test_special_chars.md，内容如下：

[CONTENT]:
# 特殊字符测试

## JSON 片段
{"key": "v



