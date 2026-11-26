# Roadmap

## Now

- Docker self-hosting
- Registration, login, SQLite persistence
- SASES Link
- HQ campaign / approval / task queue
- X adapter
- SASES Control MCP/CLI
- MCP client for external tools (experimental)
- Skill registry (`skills/*/SKILL.md`)
- Session event log (`session_events`)
- Plugin registry (metadata MVP)
- Opt-in tool plugin runtime
- Memory store (global and session)
- Cloud browser smoke test

## Next

- 小红书 adapter
- 抖音 adapter
- TikTok adapter
- Blogger adapter
- Better adapter error reporting and screenshots
- Deployment guide improvements

## Later

- Hosted plan and usage metering
- Multi-tenant workspace
- CDK/license verification service
- More platform adapters from the community

## Not planned

- Claude account sharing or bypassing platform bans
- Bulk unsolicited messaging
- Selling platform accounts

## How to contribute

- Pick an `adapter` issue.
- Follow `docs/build-your-own-sases-adapter.md`.
- Add a `check_login`, `publish`, and receipt.
- Test with dry-run first.
- Open a PR with screenshots and failure cases.
