# Self-hosting SASES on a cloud server

This guide is for running SASES on your own Linux server. It does not require
access to any private deployment.

## Requirements

- Ubuntu 22.04 or 24.04
- 2 vCPU / 4 GB RAM minimum
- 20 GB disk
- A domain name (recommended)
- A model API key (for example DeepSeek)

## Quick start with Docker

```bash
git clone https://github.com/SI-sases/sases.git
cd sases/deploy/docker
cp .env.example .env
nano .env
docker compose up -d --build
curl http://127.0.0.1:8001/version
```

The service listens on `127.0.0.1:8001` only. Put a reverse proxy in front of it.

## Configuration

| Variable | Description |
|---|---|
| `SASES_NODE_ID` | Any stable name for this instance |
| `SASES_DB_PATH` | SQLite path inside the container (`/data/users.db`) |
| `SASES_DISABLE_LOCAL_EMBEDDING` | Set to `1` on cloud servers |
| `EMBEDDING_MODE` | `api` |
| `DEEPSEEK_API_KEY` | Model provider key |
| `SASES_BASE_URL` | Public HTTPS URL |

Do not commit `.env`.

## HTTPS with Caddy

Copy `Caddyfile.example` to `Caddyfile`, replace the domain, then run Caddy
with ports 80 and 443. Caddy obtains and renews certificates automatically.

## First login

Open `https://your-domain/` and create the first account. Configure the model
API key in Settings if it is not already provided by `.env`.

## Data and backups

The SQLite database lives in the `data/` volume.

```bash
docker compose stop sases
tar czf sases-backup-$(date +%F).tgz data .env
docker compose start sases
```

To restore, stop the service, extract the archive in place, and start again.

## Upgrade

```bash
git pull
docker compose up -d --build
```

Back up `data/` and `.env` before upgrading.

## Firewall

```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

Do not expose port 8001 publicly.

## Troubleshooting

```bash
docker compose logs -f sases
docker compose ps
curl -v http://127.0.0.1:8001/version
```

If the container exits, check `.env` and the logs first.

## Security notes

- Keep `.env` at mode 600.
- Never commit API keys, databases, or node identities.
- Use HTTPS.
- Take regular backups.
- Restrict registration if the instance is public.
