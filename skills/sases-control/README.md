# SASES Control Skill

让 agent 通过 SASES HQ 操作多个 SASES 实例。

## 两种用法

### 1. CLI

```bash
export SASES_HQ_URL=https://your-sases.example.com
export SASES_HQ_TOKEN=...
python scripts/sases_ctl.py campaigns
```

### 2. MCP stdio server

```bash
export SASES_HQ_URL=https://your-sases.example.com
export SASES_HQ_TOKEN=...
python skills/sases-control/mcp_server.py
```

MCP 客户端配置：

```json
{
  "mcpServers": {
    "sases": {
      "command": "python",
      "args": ["/absolute/path/to/skills/sases-control/mcp_server.py"],
      "env": {
        "SASES_HQ_URL": "https://your-sases.example.com",
        "SASES_HQ_TOKEN": "replace-me"
      }
    }
  }
}
```

## 工具

```text
sases_list_campaigns
sases_create_campaign
sases_approve_campaign
sases_list_tasks
```

## 规则

- 先创建，审批后才执行。
- 不伪造回执。
- 不操作未授权账号。
- 内容带 GitHub 仓库。
- 不把 token 写进仓库。

## 兼容

CLI 和 MCP 都是普通 HTTP/JSON-RPC，可用于：

```text
DeepSeek Harness
Claude
其他支持 MCP 的 agent
自有自动化
```
