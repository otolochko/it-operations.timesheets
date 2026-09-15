# Claude Navigation and Guidelines

Operational router, universal invariants, execution commands, and environment definitions for this repository.

## Where to Read for X

| Topic | Primary Reference |
|---|---|
| Architecture layout, layering rules, request lifecycle, DB schema | [`docs/claude/architecture.md`](docs/claude/architecture.md) |
| Coding standards, response contracts, pagination, error handling | [`docs/claude/conventions.md`](docs/claude/conventions.md) |
| Feature specifications, router and service maps, gotchas | [`docs/claude/features.md`](docs/claude/features.md) |
| Jira Cloud HTTP client methods, auth headers, retry backoff | [`docs/claude/api-clients.md`](docs/claude/api-clients.md) |
| Background sync worker, APScheduler lifecycle, watermark cursor | [`docs/claude/async-tasks.md`](docs/claude/async-tasks.md) |
| Frontend directory structure, theme tokens, UI components, tests | [`docs/claude/frontend.md`](docs/claude/frontend.md) |
| Docker Compose deployment, reverse proxy setup, upgrade steps | [`docs/deployment.md`](docs/deployment.md) |
| Documentation standard, update triggers, review checklist | [`docs/documentation-rules.md`](docs/documentation-rules.md) |

## Invariants

1. `work_date` (`backend/app/core/worklog_time.py`) is always derived from a worklog's own local UTC offset, identically whether computed from raw Jira JSON (`work_date_from_jira_json`) or a stored DB row (`work_date_from_row`) — never by normalizing to UTC first (`.astimezone(timezone.utc)` must never appear in `backend/app/core/worklog_time.py`).
2. No Jira HTTP call happens on any user-facing request path — `backend/app/services/timesheet_service.py` and `backend/app/routers/timesheets.py` never import `app.core.jira_http`.
3. All backend env var access goes through `backend/app/core/config.py`'s `settings` singleton — no other module reads `os.environ` directly.
4. No hardcoded hex or rgb color literals in any frontend `.tsx` file — always a Tailwind class backed by a CSS custom property (`grep -rnE "#[0-9a-fA-F]{3,8}\b|rgba?\(" frontend/src --include=*.tsx` returns nothing).
5. The `--log-*` CSS token family is confined to `globals.css`, `tailwind.config.ts`, `tokens.ts`, and `LogViewer.tsx` — never reused in the main app palette.
6. A sync run (`backend/app/services/sync_service.py: run_sync`) advances `sync_state.last_watermark` only on full success; a failed run leaves the watermark untouched so reruns remain safe and idempotent.
7. `POST /api/sync/worklogs` refuses to start a second run while one is already in progress, returning the existing running `SyncRun` instead of racing on `sync_state`.
8. Cron expressions are validated with APScheduler's own `CronTrigger.from_crontab` in `backend/app/services/scheduler.py`'s `validate_cron()`, preventing parser-mismatch crashes.
9. Every row and header written in `backend/app/services/export_service.py` passes through `_safe_row` (or `_safe_cell`) to sanitize user-controlled strings against spreadsheet formula injection.

## Run Commands

- **Full stack (Docker Compose)**: `docker compose up --build`
- **Backend development server**: `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload`
- **Backend database migrations**: `cd backend && alembic upgrade head`
- **Backend test suite**: `cd backend && PYTHONPATH=. .venv/bin/python3 -m pytest tests/ -v`
- **Frontend development server**: `cd frontend && npm run dev`
- **Frontend test suite**: `cd frontend && npm run test`
- **Frontend production build**: `cd frontend && npm run build`

## Key Env Vars

| Var | Purpose |
|---|---|
| `POSTGRES_USER` | PostgreSQL superuser username |
| `POSTGRES_PASSWORD` | PostgreSQL user password |
| `POSTGRES_DB` | PostgreSQL database name |
| `DATABASE_URL` | SQLAlchemy connection string (`postgresql+psycopg://...`) |
| `JIRA_BASE_URL` | Base URL of the Jira Cloud instance (e.g. `https://your-domain.atlassian.net`) |
| `JIRA_EMAIL` | Technical user email address for Jira Basic Auth |
| `JIRA_API_TOKEN` | API token for technical user Jira Basic Auth |
| `JIRA_MAX_RETRIES` | Maximum retry attempts for failed/throttled Jira HTTP requests |
| `JIRA_RETRY_BASE_SECONDS` | Initial backoff delay in seconds for exponential retry sleep |
| `JIRA_TIMEOUT_SECONDS` | Per-request connect/read/write/pool timeout in seconds for the Jira HTTP client |
| `JIRA_PROJECT_KEYS` | Comma-separated list of Jira project keys to sync (e.g. `PROJ1,PROJ2`) |
| `SYNC_DEFAULT_CRON` | Fallback 5-field cron expression for background sync (e.g. `0 * * * *`) |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed origins (defaults to `http://localhost:3000`, never `*`) |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend build-time backend URL consumed by the browser (defaults to `http://localhost:8000`) |

## Known Limitations

- **No application-level authentication**: The application contains no login or user management; deployment must use authenticated VPN/SSO at the reverse proxy, keep Compose ports loopback-only, and set `CORS_ALLOWED_ORIGINS` to the specific frontend host, never `*`.
- **Global worklog change feed**: Jira Cloud `worklog/updated` and `worklog/deleted` endpoints return changes across the entire instance. The sync engine fetches worklog and issue details globally and filters by project key afterwards; initial syncs for large organizations can take significant time.
- **Fixed ISO week start**: Week aggregation uses PostgreSQL `date_trunc('week', work_date)`, which defaults to ISO weeks starting on Monday with no option for alternative week starts.
