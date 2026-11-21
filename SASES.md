# SASES 项目指令（只读约束）

> 本文件是稳定前缀，只放"长期有效"的约束，不放临时任务。
> 本地覆盖：`SASES.local.md`（不进 git，优先于本文件）。

## 架构约束

- 单体 FastAPI + SQLite；不引入新框架、不新增顶层目录。
- 新能力优先改现有文件；一个能力最多新增一个文件。
- 统一工具入口：`core/tool_gateway.invoke_tool(tool_id, params)`；禁止绕过网关直接调 `harness_runtime`。
- 状态只存三处：进度 `run_trace`、产物 `run_artifacts`、结论 `messages`；不要新增第二套状态。
- 数据库建表必须幂等（`CREATE TABLE IF NOT EXISTS` + `_ensure_column`），要兼容空库冷启动。

## 禁止修改

- `users.db`（运行库）、`.env`、`data/tools_admin_token.txt`
- `venv312/`、`harness_modules/_external/`（用户安装的工具，只在沙箱里跑）
- 不要执行 `git push --force`、不要删除 `.git`

## 编码规范

- Python 3.12，UTF-8；中文注释可以，标识符用英文。
- 改 API 必须同时改：Pydantic 模型 → service → SQL → 前端调用。
- 新增前端模块用 ES module，挂到现有入口（`main.js` / `chat.js`），不新建页面。
- 所有外部输入（URL、文件路径、工具参数）必须做边界检查。

## 验收命令

```powershell
# 语法
C:\Users\xiaomai\sases\venv312\Scripts\python.exe -m py_compile <files>
# 服务
Invoke-WebRequest http://127.0.0.1:8001/version
# 重启
Set-Content C:\Users\xiaomai\sases\restart_signal.txt restart
```

UI 改动必须用无头 Chrome 截图验证；后端改动必须跑一次真实调用（不能只看编译通过）。

## 当前阶段

- A1 token 计量、A2 会话压缩已完成。
- 下一步：A3 prompt 顺序/缓存、A4 本文件接入、B1 fast 模式。
- 服务器 Node-A/B 仍落后本地，部署时先 `git stash` 现场再同步。

## 任务边界

- 涉及超过 3 个文件的修改，先拆解再执行。
- 不确定的接口/字段，先 `grep_code` + `file_read`，禁止凭记忆写。
- 每次声称"完成"必须附：改了哪些文件、跑了什么验证、结果是什么。
