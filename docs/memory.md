# Memory

SASES stores small user memories in SQLite.

## Scopes

```text
global   available across sessions
session  scoped to one conversation
```

## API

```text
GET    /memory?scope=global
GET    /memory?scope=session&session_id=123
POST   /memory
DELETE /memory/{id}
```

Write:

```json
{
  "key": "preferred_language",
  "value": "zh",
  "scope": "global"
}
```

## Rules

- Per-user isolation.
- Upsert by `(user_id, scope, session_id, key)`.
- `session` requires `session_id`.
- No automatic prompt injection yet; callers read memory explicitly.
- Do not store passwords, tokens, or private keys.

## Next

- Inject selected memories into the agent prompt
- Memory extraction after a conversation
- Search and ranking
