# Architecture

## Roles

```text
HQ
  campaign / approval / task queue / audit

Executor
  logged-in browser / platform adapter / receipt

Cloud browser
  public pages / screenshots / scraping without a user session
```

## Flow

```text
Agent or human
  → create campaign
  → approve
  → queued task
  → executor claims
  → adapter publishes
  → receipt returns to HQ
```

## HQ API

```text
GET  /hq/campaigns
POST /hq/campaigns
POST /hq/campaigns/{id}/approve
GET  /hq/tasks
POST /hq/tasks/claim
POST /hq/tasks/{id}/receipt
```

## Adapter contract

```python
class Adapter:
    platform = "example"

    def check_login(self, page) -> str: ...
    def publish(self, task: dict, page) -> dict: ...
```

Receipt:

```json
{
  "ok": true,
  "platform": "example",
  "url": "https://example.com/post/123",
  "screenshot": "data/screenshots/example-123.png",
  "published_at": "2026-11-26T00:00:00+08:00"
}
```

## Browser sessions

- **Local executor:** Edge/Chromium CDP with the operator's logged-in profile.
- **Cloud browser:** headless Chromium for public pages; no user session.

Do not expose CDP to the public network.

## Data

- HQ SQLite: users, campaigns, tasks, receipts, audit.
- Executor: local browser profile and screenshots.
- Secrets: `.env`, not Git.

## Network

Nodes may use a private overlay network for task traffic. Public docs do not
publish node addresses. Keep management ports private.
