# Production Deployment Guide

Deployment topology, environment configuration, container build isolation, network security, and upgrade procedures.

## Deployment Architecture

The production environment runs via Docker Compose with three interconnected services:

```
[ Internal Corporate Network / VPN ]
                 │
                 ▼
     [ Authenticated Nginx Reverse Proxy / Ingress ]
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
| `postgres` | `postgres:16` | `127.0.0.1:5432` | PostgreSQL persistence storing issues, worklogs, and sync state on volume `postgres_data`. |
| `backend` | Dockerfile (`python:3.12.7-slim`) | `127.0.0.1:8000` | FastAPI REST API and APScheduler background synchronization worker. |
| `frontend` | Dockerfile (`node:22.12.0-slim`) | `127.0.0.1:3000` | Next.js production server. |

## Network Security and Access Control

- **No Application Authentication**: The application contains no user accounts, passwords, or session tokens. Put the reverse proxy behind corporate VPN and SSO/OIDC (or an equivalent authenticated network boundary) before allowing any user access.
- **Loopback Ports Only**: Compose publishes `3000`, `8000`, and `5432` only on `127.0.0.1`; Docker-network services still communicate by service name. Never change these bindings to a public interface. PostgreSQL is for host-local administration and must not be proxied.
- **CORS Protection**: Ensure `CORS_ALLOWED_ORIGINS` in `.env` is set to the explicit internal domain of the frontend (e.g. `https://timesheets.internal.company`). **Never** set this value to wildcard `*`.
- **Least-Privilege Environment**: Compose reads `.env` only for interpolation. PostgreSQL receives only `POSTGRES_*`, the backend receives database/Jira/runtime settings, and the frontend receives no runtime secrets.

## Build Context Security

Both `backend/.dockerignore` and `frontend/.dockerignore` strictly exclude sensitive files:

- Excludes `.env` to prevent host secrets from being copied into container images during `docker build`.
- Excludes `.venv`, `node_modules`, `.next`, `__pycache__`, and `.git` to ensure deterministic builds.
- Production containers run as unprivileged users. The frontend build uses `npm ci`; its runtime image contains production dependencies only. The backend production image excludes pytest tooling.

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
| `NEXT_PUBLIC_API_BASE_URL` | Public backend route or proxy path used by browsers (e.g. `https://timesheets.internal.corp`) |

`NEXT_PUBLIC_API_BASE_URL` is embedded into the JavaScript bundle during `docker compose build`.
Changing it requires rebuilding the frontend image; setting it on a running frontend container has
no effect. For a same-origin Nginx deployment, set it to the public origin (for example,
`https://timesheets.internal.corp`) so browser requests reach the proxy's `/api/` location.

## Reverse Proxy Configuration (Nginx)

Place this rate-limit zone in Nginx's top-level `http {}` block, once per Nginx instance:

```nginx
limit_req_zone $binary_remote_addr zone=timesheets_api:10m rate=10r/s;
```

When deploying behind Nginx on a host machine, protect the server with the organization SSO/OIDC
mechanism (shown as an include below) and use bounded requests:

```nginx
server {
    listen 443 ssl http2;
    server_name timesheets.internal.corp;

    ssl_certificate     /etc/ssl/certs/internal.crt;
    ssl_certificate_key /etc/ssl/private/internal.key;

    # This file must reject unauthenticated users before proxying requests.
    include /etc/nginx/snippets/timesheets-sso.conf;

    client_max_body_size 1m;
    client_body_timeout 15s;
    send_timeout 30s;

    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Route backend API calls
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        limit_req zone=timesheets_api burst=20 nodelay;
        proxy_connect_timeout 5s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
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

The SSO include is intentionally organization-specific; a network allow-list alone is insufficient
when the VPN serves more users than should access timesheets. Keep Nginx as the sole external
entrypoint. If frontend-originated API calls need a Content-Security-Policy, configure that policy
in exactly one layer (the reverse proxy or the frontend) to avoid conflicting headers.

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

To inspect the resolved Compose structure without printing interpolated secret values:

```bash
docker compose config --no-interpolate
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
