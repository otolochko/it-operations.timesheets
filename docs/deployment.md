# Production Deployment Guide

Deployment topology, environment configuration, container build isolation, network security, and upgrade procedures.

## Deployment Architecture

The production environment runs via Docker Compose with three interconnected services:

```
[ Internal Corporate Network / VPN ]
                 │
                 ▼
     [ Nginx Reverse Proxy / Ingress ]
        │                       │
        ▼                       ▼
 frontend:3000 (Next.js)   backend:8000 (FastAPI)
                                │          │
            ┌───────────────────┘          └───────────────────┐
            ▼                                                  ▼
 postgres:5432 (PostgreSQL 16)                     Jira Cloud REST API v3
```

| Service | Container Image | Port | Description |
|---|---|---|---|
| `postgres` | `postgres:16` | 5432 | PostgreSQL persistence storing issues, worklogs, and sync state on volume `postgres_data`. |
| `backend` | Dockerfile (`python:3.12.7-slim`) | 8000 | FastAPI REST API and APScheduler background synchronization worker. |
| `frontend` | Dockerfile (`node:22.11.0-slim`) | 3000 | Next.js 14 production standalone server. |

## Network Security and Access Control

- **No Application Authentication**: The application contains no user accounts, passwords, or session tokens.
- **Restricted Access Only**: All containers and host ports must be restricted to an internal private network or corporate VPN. Never expose host ports `3000`, `8000`, or `5432` to the public internet.
- **CORS Protection**: Ensure `CORS_ALLOWED_ORIGINS` in `.env` is set to the explicit internal domain of the frontend (e.g. `https://timesheets.internal.company`). **Never** set this value to wildcard `*`.

## Build Context Security

Both `backend/.dockerignore` and `frontend/.dockerignore` strictly exclude sensitive files:

- Excludes `.env` to prevent host secrets from being copied into container images during `docker build`.
- Excludes `.venv`, `node_modules`, `.next`, `__pycache__`, and `.git` to ensure deterministic builds.

## Environment Configuration

Create `.env` in the repository root by copying `.env.example`:

```bash
cp .env.example .env
```

| Variable | Recommended Production Value |
|---|---|
| `POSTGRES_USER` | Production database username |
| `POSTGRES_PASSWORD` | Strong random password string |
| `POSTGRES_DB` | Production database name (`timesheets`) |
| `DATABASE_URL` | `postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}` |
| `JIRA_BASE_URL` | Organization Jira Cloud base URL (`https://<domain>.atlassian.net`) |
| `JIRA_EMAIL` | Dedicated technical service account email |
| `JIRA_API_TOKEN` | Atlassian API token generated for the service account |
| `JIRA_MAX_RETRIES` | `5` |
| `JIRA_RETRY_BASE_SECONDS` | `1.0` |
| `JIRA_TIMEOUT_SECONDS` | `30.0` |
| `JIRA_PROJECT_KEYS` | Comma-separated list of target project keys (e.g. `INFRA,OPS,PLAT`) |
| `SYNC_DEFAULT_CRON` | Cron schedule for background sync (e.g. `0 * * * *` for hourly) |
| `CORS_ALLOWED_ORIGINS` | Internal domain (e.g. `https://timesheets.internal.corp`) |
| `NEXT_PUBLIC_API_BASE_URL` | Internal backend route or proxy path (e.g. `https://timesheets.internal.corp`) |

## Reverse Proxy Configuration (Nginx)

When deploying behind Nginx on a host machine:

```nginx
server {
    listen 443 ssl http2;
    server_name timesheets.internal.corp;

    ssl_certificate     /etc/ssl/certs/internal.crt;
    ssl_certificate_key /etc/ssl/private/internal.key;

    # Route backend API calls
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Route frontend pages and assets
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Initial Deployment Procedure

1. Clone the repository to the host server.
2. Prepare the `.env` file with production parameters.
3. Build the Docker images:
   ```bash
   docker compose build
   ```
4. Start the database container:
   ```bash
   docker compose up -d postgres
   ```
5. Apply Alembic database migrations:
   ```bash
   docker compose run --rm backend alembic upgrade head
   ```
6. Start all services:
   ```bash
   docker compose up -d
   ```
7. Verify operational status:
   ```bash
   docker compose ps
   docker compose logs -f backend
   ```

## Upgrade Procedure

To deploy codebase updates with minimal downtime:

1. Fetch latest changes from source control:
   ```bash
   git pull origin main
   ```
2. Build updated container images:
   ```bash
   docker compose build
   ```
3. Run database migrations against the running PostgreSQL service:
   ```bash
   docker compose run --rm backend alembic upgrade head
   ```
4. Recreate and restart backend and frontend containers:
   ```bash
   docker compose up -d --no-deps backend frontend
   ```
5. Confirm successful restart:
   ```bash
   docker compose ps
   ```

For navigation and command references, see [`../CLAUDE.md`](../CLAUDE.md). For public project overview, see [`../README.md`](../README.md).
