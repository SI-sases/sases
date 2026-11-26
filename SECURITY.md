# Security policy

## Reporting

Do not open a public issue for a vulnerability. Contact the maintainer through
the GitHub profile or a private security advisory.

Include:

- affected version/commit
- reproduction steps
- impact
- suggested fix, if known

## Scope

SASES handles:

- user accounts and sessions
- SQLite database
- model API keys
- optional platform browser sessions

## Rules

- Never commit `.env`, `users.db`, cookies, tokens, or private keys.
- Keep `8001` private; use HTTPS.
- Use a dedicated browser profile for automation.
- Do not expose CDP to the public network.
- Rotate any key that may have been exposed.
- Back up `data/` and `.env` before upgrades.

## Supported versions

Security fixes target the latest release and `main`.
