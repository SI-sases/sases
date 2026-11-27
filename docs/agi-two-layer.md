# Two-layer AGI (local main + sub)

## Status

P0 shadow mode is implemented in `agi/`:

```text
agi/protocol.py   structured messages
agi/tools.py      one shared registry, main/sub profiles
agi/runtime.py    observe -> diagnose -> record
agi/main_agi.py   CLI entry
agi/server.py     loopback event/control server
agi/sub_agi.py    sub heartbeat adapter
agi/deploy.py     staging/promote/rollback plans (dry run)
agi/staging.py    run candidate on alternate port and verify
agi/leader.py     single-main lease per scope (local/fleet)
agi/autopilot.py  observe + report loop (no production mutation)
agi/report.py     human-readable fleet report
agi/policy.py     main-auto vs human-required routing
agi/escalation.py open items for the commander
agi/playbooks/    health_check, publish_platform, deploy_node
```

The main AGI currently does **read-only observation**:

```text
GET /health
GET /version
POST /events (sub AGI heartbeat)
write agi_events / agi_nodes / agi_runs
```

It does not edit a running tree, restart production, or change `users.db`.

## Main AGI control server

```bash
python -m agi.server
```

Bind:

```text
127.0.0.1:8099
```

Token:

```text
data/agi.token
```

Endpoints:

```text
GET  /health
GET  /events?limit=50
POST /events
POST /observe
```

Sub AGI push:

```bash
python -m agi.sub_agi --once --post http://127.0.0.1:8099
```

Deploy tools return **plans only**:

```text
deploy.stage
deploy.promote
deploy.rollback
```

All are main-only and `requires_approval=true`.

Task tools:

```text
task.list     main/sub, read
task.create   main only, write
task.claim    main/sub, write
task.receipt  main/sub, write
browser.open  main only, read
browser.fill  main only, write
browser.click main only, write
browser.reddit_post main only, write (dry-run by default)
recovery.plan main only, read
support.classify main/sub, read
support.kb_search main/sub, read
support.draft main/sub, read
support.ticket main/sub, write
```

Browser worker:

```text
scripts/browser_act.py
```

Set `SASES_BROWSER_PYTHON` if the main AGI runs under an embedded Python
without Playwright.

Reddit playbook:

```text
agi/playbooks/reddit_publish.json
scripts/browser_reddit.py
```

`browser.reddit_post` defaults to `dry_run=true`; it fills title/body and
screenshots without submitting.  A separate real-submit step is required.

## Support

Knowledge base:

```text
agi/support_kb/*.md
```

Flow:

```text
classify
-> search KB
-> draft answer
-> ticket if unresolved
-> human for money/legal/security
```

L1/L2/L3 tickets are stored in `support_tickets`; refunds, invoices, account
deletion, security, and legal requests are routed to the human.

## Staging verifier

```bash
python -m agi.staging --root D:\sases_build\portable_test2 --port 8030
```

It starts the candidate package on an alternate loopback port, checks
`/health` or `/version`, then kills the process tree.  It never touches the
production port/tree.

Tool:

```text
deploy.verify  (main-only, candidate path required)
```

## Leader lock

One active main per scope:

```text
POST /leader/acquire  {scope,owner,ttl}
POST /leader/renew    {scope,owner,ttl}
POST /leader/release  {scope,owner}
GET  /leader?scope=fleet
```

A crashed owner releases the lock by lease expiry; a second owner gets 409
while the lease is active.

## Autopilot (observe/report only)

```bash
python -m agi.autopilot --once --base-url http://127.0.0.1:8001
python -m agi.autopilot --interval 60
```

Report:

```text
reports/agi_report.md
```

`kind` distinguishes:

```text
client  local packaged client
cloud   cloud SASES node
```

Autopilot does not promote, rollback, restart, or edit code.

## Supervision policy

The main AGI handles routine work first:

```text
health.observe
event.record
report.generate
task.retry
task.reroute
config.low_risk
staging.verify
```

It escalates to the commander:

```text
code.change
db.migration
deploy.promote
deploy.rollback
service.restart.production
security.change
network.change
billing.change
critical / repeated errors
unknown actions
```

Open items:

```text
GET /escalations
reports/agi_report.md -> "需要指挥官处理"
```

## Run

```bash
python -m agi.main_agi --once --base-url http://127.0.0.1:8001
python -m agi.main_agi --interval 30 --base-url http://127.0.0.1:8001
```

Database:

```text
data/agi.db
```

Override:

```text
SASES_AGI_DB
SASES_AGI_TARGET
```

## Tool rules

One implementation, two profiles:

```text
main: read + dispatch + propose + stage/promote/rollback (approval)
sub:  claim + execute + receipt + report
```

Main does not get `shell`, `db.write`, or arbitrary file writes.

## Playbooks

```text
agi/playbooks/health_check.json
agi/playbooks/publish_platform.json
agi/playbooks/deploy_node.json
```

`publish_platform` and `deploy_node` are the replicated workflow targets;
their mutation tools are intentionally not enabled in P0.

## Package

The portable build now includes:

```text
agi/
启动主AGI.bat
```

Required file:

```text
agi/main_agi.py
```

## Next

```text
P1: event ingestion from sub AGI
P1: staging/promote/rollback tools
P1: shadow comparison against human actions
P2: low-risk auto-remediation
```
