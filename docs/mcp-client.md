# MCP Client (experimental)

SASES can call external MCP servers over stdio.

This is disabled by default.

## Enable

```env
SASES_MCP_ALLOW=1
```

## API

```text
GET    /mcp/servers
POST   /mcp/servers
DELETE /mcp/servers/{id}
POST   /mcp/servers/{id}/test
GET    /mcp/servers/{id}/tools
POST   /mcp/call
```

Add a stdio server:

```json
{
  "name": "sases-control",
  "command": "python",
  "args": ["/path/to/mcp_server.py"],
  "env": {
    "SASES_HQ_URL": "http://127.0.0.1:8001",
    "SASES_HQ_TOKEN": "..."
  }
}
```

The API response redacts `env` values and returns only `env_keys`.

## Security

- Only authenticated users can manage servers.
- Server commands can execute locally; use only trusted servers.
- No arbitrary shell is accepted through the chat prompt.
- Server processes are short-lived and killed after each operation.
- A read timeout kills a stuck server.
- Do not put tokens in logs or Git.

## Limitations

- stdio transport only in this MVP.
- No OAuth/remote HTTP transport yet.
- Tool calls are not yet routed through the agent's normal tool policy.
- Keep `SASES_MCP_ALLOW=0` unless you need it.

## UI

MCP tools appear in the existing **能力 / Capabilities** capsule:

```text
能力 → MCP → select server/tool
```

Selected tools become a capsule chip and are sent with the chat request as
`enabled_mcp_ids`. The agent loop adds those tools to its schema and calls them
through `tool_gateway` as `mcp.<server>.<tool>`.

## Tool gateway

MCP tools are routed through the normal tool gateway:

```text
mcp.<server>.<tool>
```

Example:

```python
invoke_tool("mcp.1.sases_list_campaigns", {})
```

`mcp.*` is classified as high risk and requires approval.

## Skills

SASES also scans `skills/*/SKILL.md`:

```text
GET /skills
GET /skills/{name}
```

Skill files are read-only; loading returns instructions, not executable code.
