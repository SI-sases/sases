# Plugins (metadata MVP)

SASES discovers plugins under `plugins/`:

```text
plugins/
  my-plugin/
    plugin.json
```

Manifest:

```json
{
  "id": "my-plugin",
  "name": "My plugin",
  "version": "1.0.0",
  "type": "tool",
  "description": "What it does"
}
```

Rules:

- `id` must match the directory name.
- `id` is lowercase letters, numbers, `_` or `-`.
- `type` is `adapter`, `tool`, or `skill`.
- `version` is required.
- New plugins are disabled by default.

## API

```text
GET  /plugins
POST /plugins/{id}/enable
POST /plugins/{id}/disable
```

All endpoints require login.

## Scope

This MVP is a **registry + opt-in tool runtime**.

It does:

- discover manifests
- enable/disable
- run `tool` plugins through a subprocess
- require `SASES_PLUGIN_ALLOW=1`
- classify `plugin.*` as high risk

It does not:

- install from npm/Git
- inject UI
- execute adapters yet
- grant shell access automatically

## Tool contract

```text
stdin  → JSON params
stdout → JSON result
exit 0
```

Example:

```json
{"entrypoint": "main.py", "type": "tool"}
```

Run through the gateway:

```python
invoke_tool("plugin.example-tool", {"x": 1})
```

or:

```text
POST /plugins/{id}/call
```

Execution is short-lived, has a 20 second timeout, and runs with the plugin
directory as cwd.

## Adding execution later

For an adapter:

```text
plugin.json → entrypoint "adapter.py" → adapter.publish(task, page)
```

For a tool:

```text
plugin.json → entrypoint "main.py" → run(params)
```

Execution must be opt-in, approved, and scoped.
