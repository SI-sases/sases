# Quick start

## Requirements

- Ubuntu 22.04 or 24.04
- 2 vCPU / 4 GB RAM
- 20 GB disk
- Docker + Docker Compose v2
- A model API key
- Optional: a domain name

## 1. Clone

```bash
git clone https://github.com/SI-sases/sases.git
cd sases/deploy/docker
cp .env.example .env
```

## 2. Configure

Edit `.env`:

```env
SASES_NODE_ID=my-sases
DEEPSEEK_API_KEY=replace-me
SASES_BASE_URL=https://sases.example.com
```

Do not commit `.env`.

## 3. Run

```bash
docker compose up -d --build
curl -fsS http://127.0.0.1:8001/version
```

If PyPI is slow:

```bash
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
  docker compose up -d --build
```

## 4. HTTPS

Caddy example:

```text
sases.example.com {
    reverse_proxy 127.0.0.1:8001
}
```

Or Nginx with WebSocket upgrade headers.

## 5. First login

Open `https://sases.example.com/` and create the first account. Configure the
model key in Settings if it is not in `.env`.

## 6. Health

```bash
docker compose ps
docker compose logs --tail=100 sases
curl -fsS http://127.0.0.1:8001/version
```

## Common failures

| Symptom | Fix |
|---|---|
| Build cannot reach Docker Hub/PyPI | Set `PIP_INDEX_URL`; use a Docker mirror |
| `ContainerConfig` error with `docker-compose` v1 | Use Docker Compose v2 (`docker compose`) |
| 8001 unreachable from another node | Bind `0.0.0.0:8001` only for internal use; keep public access behind HTTPS |
| Database lost | Do not run `docker compose down -v`; restore `data/` and `.env` |

## Upgrade

```bash
cd /opt/sases
git fetch --tags
git checkout v1.0.0
cd deploy/docker
tar czf ../sases-backup-$(date +%F-%H%M).tgz data .env
docker compose up -d --build
curl -fsS http://127.0.0.1:8001/version
```
