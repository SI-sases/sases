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

Use Docker Compose v2 (`docker compose`). The legacy `docker-compose` v1 CLI is
not supported on current Docker releases and can fail with `ContainerConfig`.

If Docker Hub or PyPI is slow or blocked, pass a mirror before building:

```bash
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
  docker compose up -d --build
```

The image is based on `python:3.12-slim` and does not install `curl`. Its
healthcheck uses Python, so do not override it with a curl-based check.

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

Back up first. The database is migrated automatically on startup, so a backup is
the only reliable rollback path.

```bash
cd /opt/sases

# 1. Back up the database and environment file
cd deploy/docker
tar czf ../sases-backup-$(date +%F-%H%M).tgz data .env

# 2. Fetch the release you want to run
cd /opt/sases
git fetch --tags
git checkout v1.0.0

# 3. Review configuration changes
cd deploy/docker
diff -u .env.example .env || true

# 4. Rebuild and recreate the container
docker compose up -d --build

# 5. Verify
curl -fsS http://127.0.0.1:8001/version
docker compose ps
docker compose logs --tail=100 sases
```

Replace `v1.0.0` with the tag you intend to run. If the server cannot reach
Docker Hub or PyPI, set a build mirror before rebuilding:

```bash
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
  docker compose up -d --build
```

Do not use `docker compose down -v`: `-v` deletes the database volume.

### Rolling back

```bash
cd /opt/sases
git checkout <previous-tag>
cd deploy/docker
docker compose up -d --build
```

If the new version has already migrated the database, also restore the backup
taken before the upgrade. Do not assume an older binary can read a newer schema.

### Notes for cloud servers

- Back up to object storage or another machine, not only the same disk.
- Keep `8001` private; expose only `80/443` through Caddy or Nginx.
- Open `22/80/443` in the cloud security group, not just `ufw`.
- Watch disk usage: Docker images and `data/` both grow.
- Run upgrades in a maintenance window and verify `/version` afterwards.

## Firewall

```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

Do not expose port 8001 publicly.

On a cloud VM, also configure the provider security group: allow `22/80/443`
inbound, and keep `8001` closed to the internet. `ufw` alone is not enough if
the security group still allows `8001`.

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
