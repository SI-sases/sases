# Tool policy and approvals

SASES classifies tools before execution.

## Risk levels

```text
read      file_read, dir_list, grep_code, web_search
write     file_write, smart_edit, git_ops, delete_block
network   web_fetch, api_call, http_async
high      ssh_exec, run_python, shell, mcp.*
unknown   anything else
```

## Modes

```env
SASES_APPROVAL_MODE=risk   # default
SASES_APPROVAL_MODE=off
SASES_REQUIRE_APPROVAL=1   # require every tool
```

## Approval

Write, network and high-risk tools require approval when a run is active.

MCP tools are always high risk:

```text
mcp.<server>.<tool>
```

## Tool gateway

MCP tools are callable through the normal gateway:

```python
invoke_tool("mcp.1.sases_list_campaigns", {})
```

The gateway checks:

```text
SASES_MCP_ALLOW
server enabled
server exists
tool result
```

## Rules

- Do not bypass the gateway with direct MCP calls from agent code.
- Do not auto-approve `mcp.*` for untrusted servers.
- Keep `SASES_MCP_ALLOW=0` unless the server is trusted.
- Log tool id, status and error; never log secrets.
