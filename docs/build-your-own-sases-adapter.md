# Build Your Own SASES Platform Adapter

SASES is a self-hosted AGI system. This guide describes the publishing
architecture and how to add your own platform adapter. It does not require any
private deployment.

## Architecture

```text
HQ
  ├── campaign
  ├── approval
  └── task queue
        │
        ▼
Local executor
  ├── logged-in browser session
  ├── platform adapter
  └── receipt
        │
        ▼
HQ audit / retry
```

Three roles:

1. **HQ** owns campaigns, approval, routing and receipts.
2. **Local executor** uses the operator's logged-in browser session.
3. **Cloud browser** handles public pages, screenshots and scraping without a
   user session.

## HQ API

```text
GET  /hq/campaigns
POST /hq/campaigns
POST /hq/campaigns/{id}/approve
GET  /hq/tasks
POST /hq/tasks/claim
POST /hq/tasks/{id}/receipt
```

A campaign contains a region, platforms and content. Approval moves its tasks
from `pending_approval` to `queued`.

## Task payload

```json
{
  "campaign_id": 1,
  "platform": "x",
  "region": "intl",
  "action": "publish",
  "payload": {
    "title": "Deploy Your Own AGI",
    "body": "...",
    "url": "https://github.com/SI-sases/sases",
    "images": []
  }
}
```

Every task should include a stable `idempotency_key` or a unique
`campaign_id + platform` pair so retries do not create duplicate posts.

## Adapter contract

Create one adapter per platform. Keep it small and explicit.

```python
class Adapter:
    platform = "example"

    def check_login(self, page) -> str:
        """Return logged_in, needs_login, or page_error."""
        raise NotImplementedError

    def publish(self, task: dict, page) -> dict:
        """Publish one task and return a receipt."""
        raise NotImplementedError
```

A receipt should contain:

```json
{
  "ok": true,
  "platform": "example",
  "url": "https://example.com/post/123",
  "screenshot": "data/screenshots/example-123.png",
  "published_at": "2026-11-26T00:00:00+08:00"
}
```

## Executor loop

```python
while True:
    task = claim_task(executor="local", platform=None)
    if not task:
        sleep(5)
        continue

    adapter = adapters[task["platform"]]
    result = adapter.publish(task, open_browser())
    post_receipt(task["id"], result)
```

Rules:

- Claim before doing work.
- Verify login before filling the form.
- Screenshot before and after publishing.
- Never retry a failed login; retry a failed upload with backoff.
- Return `adapter_not_implemented` rather than a fake success.
- Keep the platform session on the executor, not on the HQ.

## Browser sessions

Two supported patterns:

### Local Edge CDP

Start Edge with a dedicated profile and remote debugging:

```text
msedge.exe --remote-debugging-port=9222 ^
  --user-data-dir=C:\edge_sases_profile ^
  --no-first-run --no-default-browser-check
```

Then connect with Playwright:

```python
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].new_page()
```

This uses the executor's real login session and does not close the operator's
normal tabs.

### Cloud browser

For public pages, screenshots and page checks, run headless Chromium in a
container:

```bash
docker build -t sases-browser:test deploy/browser
docker run --rm --shm-size=512m sases-browser:test \
  python -c "from playwright.sync_api import sync_playwright; ..."
```

The cloud browser has no user session. Use it for public pages, not for
platform posts that require login.

## Adding a new platform

1. Write `check_login(page)`.
2. Write `publish(task, page)`.
3. Take a screenshot.
4. Return a receipt with the public URL.
5. Add the platform to the allowed task list.
6. Test with `--dry-run` before a real post.
7. Record the test in the optimization ledger.

## Security

- Never put passwords, cookies or storage state in Git.
- Keep the HQ database and `.env` private.
- Use HTTPS.
- Approve campaigns before they enter the queue.
- Keep the executor's browser profile separate from the operator's normal Edge
  profile.
- Do not expose internal node addresses in public docs.

## Reference implementation

- Repository: https://github.com/SI-sases/sases
- HQ module: `core/hq.py`
- HQ routes: `core/api_routes/hq_routes.py`
- Local executor: `scripts/hq_executor.py`
- Cloud browser: `deploy/browser/Dockerfile`
- Release: https://github.com/SI-sases/sases/releases/tag/v1.0.0

The adapter is intentionally small: one login check, one publish action, one
receipt. If a platform changes, only that adapter needs to change.
