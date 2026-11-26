# Marketplace

SASES has a read-only marketplace index.

```text
marketplace/index.json
```

Entry:

```json
{
  "id": "sases-control",
  "type": "skill",
  "name": "SASES Control",
  "description": "MCP + CLI control for self-hosted SASES instances.",
  "url": "https://github.com/SI-sases/sases-control",
  "version": "1.0.0"
}
```

Types:

```text
skill / plugin / workflow / adapter
```

## API

```text
GET /marketplace?q=&type=
GET /marketplace/{id}
```

All endpoints require login.

## Scope

This is an index, not an installer.

It does not:

- install packages
- execute plugins
- fetch remote code
- add UI

It lets callers discover official entries and their source URLs.

## Next

- A capsule entry for browsing the index
- Signed entries
- Install actions with approval
