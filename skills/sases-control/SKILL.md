# SASES Control

AI 时代 AGI 可操控系统：让 agent 通过 SASES HQ 创建活动、审批、查看任务和回执。

## 适用

- DeepSeek Harness
- Claude / 其他支持 shell 或 HTTP 的 agent
- 任何能执行 Python 的自动化环境

## 配置

```bash
export SASES_HQ_URL=http://127.0.0.1:8001
export SASES_HQ_TOKEN=<JWT>
# 或执行器 token
export SASES_LINK_TOKEN=<shared token>
```

## 命令

```bash
python scripts/sases_ctl.py campaigns
python scripts/sases_ctl.py create --name "sases-v1" --region cn --platform x --body "SASES https://github.com/SI-sases/sases"
python scripts/sases_ctl.py approve 1
python scripts/sases_ctl.py tasks
python scripts/sases_ctl.py claim --platform x
python scripts/sases_ctl.py receipt 1 --status done --url https://x.com/...
```

## Agent 使用规则

1. 先创建 campaign，不直接发布。
2. 必须审批后才 claim。
3. 失败返回 `failed`，不要伪造 `done`。
4. 回执带 URL/截图。
5. 不操作未授权账号。
6. 所有内容带 GitHub 仓库。

## 输出

所有命令输出 JSON，便于 agent 解析：

```json
{"status": 200, "body": "..."}
```

## 下一步

- 包装成 MCP server
- 发布 DeepSeek H 社区插件
- 增加多实例管理
