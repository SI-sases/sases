# Workflows

SASES supports file-based tool workflows.

```text
workflows/
  read-readme/
    workflow.json
```

Manifest:

```json
{
  "id": "read-readme",
  "name": "Read README",
  "description": "Read the repository README.",
  "steps": [
    {
      "tool": "file_read",
      "params": {"file_path": "README.md"}
    }
  ]
}
```

## Rules

- `id` must match the directory name.
- 1–20 steps.
- Each step has `tool` and optional `params`.
- `{{name}}` placeholders are replaced from the run input.
- Steps run sequentially; the first failure stops the run.
- Write/network/high-risk steps require `approve=true`; otherwise the run
  returns `approval_required`.
- Tool calls go through `tool_gateway`.

## API

```text
GET  /workflows
GET  /workflows/{id}
POST /workflows/{id}/run
```

Run:

```json
{
  "params": {"name": "SASES"},
  "approve": false
}
```

## Scope

This is a tool pipeline MVP, not a full DAG or LLM workflow engine.

Not included:

- branching/parallel steps
- agent/subagent steps
- retries
- UI

## Storage

Each run is stored in `workflow_runs` with status and step results.
