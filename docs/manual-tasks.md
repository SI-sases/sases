# Manual publishing tasks

Not every platform has an adapter. For those, SASES uses a **manual task**:
the content is queued in HQ, a human claims it, posts in the app, and returns
a receipt.

## Create

```bash
python scripts/sases_ctl.py create \
  --name "xhs-testers-01" \
  --region cn \
  --platform xiaohongshu \
  --title "Claude 用不了之后..." \
  --body "..." \
  --manual
```

Approve:

```bash
python scripts/sases_ctl.py approve <campaign_id>
```

## Claim

Human executor:

```bash
python scripts/sases_ctl.py claim --platform xiaohongshu --manual
```

Automated executor:

```text
claims only manual=false tasks
```

## Receipt

```bash
python scripts/sases_ctl.py receipt <task_id> --status done --url "https://..."
```

## Rules

- `manual=true` is stored in the task payload.
- The browser executor skips manual tasks.
- A human must claim and return a URL.
- A screenshot can be attached in a later receipt extension.
- No credentials are stored in the campaign.

## Why

This is the fallback when:

- the platform has no adapter
- the page needs a logged-in human
- the page shows an anti-bot/blank state
- the account is region-bound

It keeps the same HQ approval and receipt model instead of a separate tool.
