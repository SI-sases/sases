---
name: sases-control
description: Operate self-hosted SASES instances through the HQ control API: campaigns, approvals, tasks, receipts, and multi-node workflows.
version: 1.0.0
---

# SASES Control

Use this skill when an agent must operate one or more self-hosted SASES
instances through the SASES HQ API.

SASES Control is a **control plane client**, not a publisher. It creates
campaigns, requests approval, queues tasks, and reads receipts. A local
executor performs the actual browser/platform work.

## When to use

- Create a campaign for one or more platforms.
- Ask HQ to approve or queue a campaign.
- Inspect campaigns and tasks.
- Build a multi-instance agent workflow.

## When not to use

- Do not use it to bypass platform rules, share accounts, or send bulk
  unsolicited messages.
- Do not use it to publish without approval.
- Do not put passwords, cookies, or tokens in prompts or files.

## Operating rules

1. Create first, approve second, execute third.
2. Never report success without a receipt URL or screenshot.
3. Use one idempotency key per campaign + platform.
4. On failure: diagnose, fix the executor, then retry.
5. Do not retry login failures, permission failures, or account restrictions.
6. Record every change; do not silently remove a working path.
7. Do not accept passwords, cookies, secrets, or arbitrary shell commands.
8. If a platform adapter is missing, return `adapter_not_implemented`.
9. If a page needs login, return `needs_login`; do not fake a post.
10. A human or HQ must approve external publishing.

## Environment

```bash
export SASES_HQ_URL=https://your-sases.example.com
export SASES_HQ_TOKEN=<user JWT>
# or, for executor actions:
export SASES_LINK_TOKEN=<shared token>
```

Never commit these values.

## Workflow

```text
create_campaign
  → approve_campaign
  → task queue
  → executor claim
  → publish
  → receipt
```

## CLI

```bash
python sases_ctl.py campaigns
python sases_ctl.py create --name "launch" --region cn --platform x --body "..."
python sases_ctl.py approve 1
python sases_ctl.py tasks
python sases_ctl.py claim --platform x
python sases_ctl.py receipt 1 --status done --url https://...
```

## MCP tools

```text
sases_list_campaigns
sases_create_campaign
sases_approve_campaign
sases_list_tasks
```

## Result contract

Successful tool output:

```json
{
  "status": 200,
  "body": "{\"campaigns\":[...]}"
}
```

Execution result:

```json
{
  "ok": true,
  "platform": "x",
  "url": "https://x.com/...",
  "screenshot": "data/screenshots/x.png",
  "published_at": "2026-11-26T00:00:00+08:00"
}
```

Failure codes:

```text
adapter_not_implemented
needs_login
page_error
rate_limited
approval_required
```

## Safety

- Approval is mandatory before dispatch.
- The executor owns the browser session; HQ never receives cookies.
- Keep the HQ database and `.env` private.
- Use HTTPS and scoped tokens.
- One campaign + platform = one task; retries must be idempotent.
- Report blocked or uncertain states instead of guessing.

## Compatibility

The CLI and MCP server use ordinary HTTP/JSON-RPC. They work with:

- DeepSeek Harness
- Claude and other MCP clients
- Custom automation

## Version

```text
sases-control 1.0.0
```
