# Two-layer AGI (local main + sub)

## Status

P0 shadow mode is implemented in `agi/`:

```text
agi/protocol.py   structured messages
agi/tools.py      one shared registry, main/sub profiles
agi/runtime.py    observe -> diagnose -> record
agi/main_agi.py   CLI entry
agi/playbooks/    health_check, publish_platform, deploy_node
```

The main AGI currently does **read-only observation**:

```text
GET /health
GET /version
write agi_events / agi_nodes / agi_runs
```

It does not edit a running tree, restart production, or change `users.db`.

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
