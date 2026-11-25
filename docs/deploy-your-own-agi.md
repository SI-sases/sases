# Deploy Your Own AGI on a Cloud Server

SASES is a self-hosted, privacy-first AI system. This guide shows how to run
your own AGI-style assistant on a Linux cloud server with Docker, HTTPS, and a
model API key.

The goal is simple:

- you own the server
- you own the database
- you own the API key
- the web UI is reachable only through HTTPS

## What you need

- Ubuntu 22.04 or 24.04
- 2 vCPU and 4 GB RAM minimum
- 20 GB free disk
- a domain name such as `agi.example.com`
- a model API key, for example from DeepSeek

## 1. Clone the repository

```bash
git clone https://github.com/SI-sases/sases.git
cd sases/deploy/docker
```

## 2. Create the environment file

```bash
cp .env.example .env
nano .env
```

Example:

```env
SASES_NODE_ID=my-agi
SASES_DB_PATH=/data/users.db
SASES_DISABLE_LOCAL_EMBEDDING=1
EMBEDDING_MODE=api
DEEPSEEK_API_KEY=replace-me
SASES_BASE_URL=https://agi.example.com
```

Do not commit this file.

## 3. Start SASES

```bash
docker compose up -d --build
curl http://127.0.0.1:8001/version
```

The service listens on `127.0.0.1:8001` only.

## 4. Put HTTPS in front

Caddy is the simplest option.

```text
agi.example.com {
    reverse_proxy 127.0.0.1:8001
}
```

Start Caddy with ports 80 and 443. Caddy obtains and renews certificates
automatically.

If you prefer Nginx, proxy to the same local port and enable WebSocket
upgrades.

## 5. Open the web UI

```text
https://agi.example.com
```

Create the first account. In Settings, confirm the model provider and API key.
If your key is already in `.env`, it will be used by the server.

## 6. Keep the data

The SQLite database is stored in the `data/` volume.

Back up:

```bash
docker compose stop sases
tar czf sases-backup-$(date +%F).tgz data .env
docker compose start sases
```

Restore by stopping the service, extracting the archive in place, and starting
it again.

## 7. Upgrade

```bash
git pull
docker compose up -d --build
```

Always back up `data/` and `.env` first.

## 8. Secure the server

```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

Keep port 8001 closed to the public.

Additional recommendations:

- use a dedicated non-root user for the project
- keep `.env` at mode 600
- enable automatic security updates
- restrict registration on public instances
- monitor disk usage and database size
- take off-site backups

## 9. Troubleshooting

```bash
docker compose logs -f sases
docker compose ps
curl -v http://127.0.0.1:8001/version
```

If the container exits, check the environment file and the logs first.

## Why self-host an AGI?

A self-hosted AGI gives you:

- data ownership
- model provider choice
- predictable cost
- no shared control plane
- the ability to run private tools and knowledge bases

SASES is designed to be modular. You can start with a single node, then add
your own tools, knowledge, and workflows.

## Next steps

- read `docs/self-hosting.md` for the full deployment guide
- configure your model provider
- create your first workspace
- back up the data directory
- keep the server and dependencies updated
