# Contributing

## Before you start

- Read `docs/architecture.md`.
- Read `docs/build-your-own-sases-adapter.md`.
- Search existing issues and discussions.
- Do not include secrets, databases, cookies, or private node addresses.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/ -v
```

Docker:

```bash
cd deploy/docker
cp .env.example .env
docker compose up -d --build
```

## Adapter contributions

1. Add `check_login(page)`.
2. Add `publish(task, page)`.
3. Return a receipt with `url` and `screenshot`.
4. Return `needs_login` / `page_error` instead of fake success.
5. Test dry-run before a real post.

## Pull requests

- One logical change per PR.
- Include why, what changed, and how it was verified.
- Include screenshots for UI or publishing changes.
- Never commit `.env`, `users.db`, `data/`, or credentials.

## License

Contributions are accepted under the MIT License.
