# Session events

SASES keeps `messages` as the chat source of truth and adds an append-only
`session_events` log for replay, recovery and agent consumers.

## Schema

```text
session_events
  id
  session_id      -- conversation id
  seq             -- per session, starts at 1
  type            -- message.created
  payload_json
  created_at
```

## Automatic capture

A SQLite trigger records every new `messages` row:

```text
messages INSERT → session_events(message.created)
```

No existing write path changes.

## Read

```text
GET /sessions/{conversation_id}/events?after_seq=0&limit=200
GET /sessions/{conversation_id}/events?backfill=true
```

`backfill=true` imports existing messages once, for old sessions.

## Limits

- Additive only: `messages` still drives the chat UI.
- No event editing or deletion.
- Backfill is skipped if events already exist.
- `seq` is per conversation; consumers should use `latest_seq`.

## Next

- Replay into a new conversation
- Fork a session at a seq
- Agent consumer for task and tool events
