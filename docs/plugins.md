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

This MVP is a **registry**, not a code loader.

It does not:

- execute plugin code
- install from npm/Git
- inject UI
- grant shell access

Execution is intentionally separate so an untrusted plugin cannot run just by
being present in the directory.

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
