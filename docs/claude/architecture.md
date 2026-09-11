# Backend Architecture

Architecture, layer boundaries, directory structure, request lifecycle, and data persistence models for the backend service.

---

## Directory Structure

All backend application code resides in `backend/app/`:

```
backend/app/
├── core/
│   ├── config.py              # Pydantic Settings singleton reading all environment variables
│   ├── db.py                  # SQLAlchemy engine, session maker, and get_db dependency
│   ├── jira_http.py           # Synchronous Jira Cloud REST client with retry logic
│   └── worklog_time.py        # Author-local calendar date derivation logic
├── models/
│   ├── __init__.py            # Exported SQLAlchemy declarative models
│   ├── issue.py               # Issue entity (id, key, project_key, summary, updated_at)
│   ├── sync_run.py            # SyncRun execution history for status inspection
│   ├── sync_schedule.py       # SyncSchedule singleton (id=1, cron_expression, project_keys)
│   ├── sync_state.py          # SyncState singleton (id=1, last_watermark timestamp cursor)
│   └── worklog.py             # Worklog entity with composite and date indexes
├── routers/
│   ├── sync.py                # POST /api/sync/worklogs, GET/PUT /api/sync/schedule, GET /api/sync/status
│   └── timesheets.py          # GET /api/timesheets, GET /api/timesheets/issues
├── schemas/
│   ├── __init__.py            # Schema package marker
│   ├── sync.py                # Pydantic request/response schemas for sync management
│   └── timesheets.py          # Pydantic schemas for grid aggregation and issue drilldown
├── services/
│   ├── scheduler.py           # APScheduler BackgroundScheduler setup and cron validation
│   ├── sync_service.py        # run_sync orchestrator for Jira data ingestion
│   └── timesheet_service.py   # Pure PostgreSQL SQL aggregation for timesheets
└── main.py                    # FastAPI app initialization, CORS middleware, lifespan scheduler startup
```

---

## Layering Rules

The backend strictly enforces unidirectional architectural layers:

```
Routers (backend/app/routers/)
  └── Services (backend/app/services/)
        └── Data Access & Models (backend/app/models/, backend/app/core/db.py)
```

1. **Jira Isolation Rule**: User-facing queries never call Jira. `backend/app/services/timesheet_service.py` and `backend/app/routers/timesheets.py` must never import `backend/app/core/jira_http.py` or execute external network requests.
2. **Sync Boundary**: Jira HTTP communication is strictly contained within `backend/app/services/sync_service.py` via `JiraClient` in `backend/app/core/jira_http.py`. For detailed client methods, see [`api-clients.md`](api-clients.md).
3. **Configuration Boundary**: No application module reads `os.environ` directly. All environment configuration passes through `backend/app/core/config.py`'s `settings` singleton.
4. **Timezone Encapsulation**: Converting worklog timestamps to calendar dates must only occur via functions in `backend/app/core/worklog_time.py`.

---

## Request Lifecycle

### Application Startup and Lifespan

`backend/app/main.py` defines an asynchronous lifespan manager:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
```

When FastAPI starts, `start_scheduler()` in `backend/app/services/scheduler.py` reads the active cron expression from the `sync_schedule` table in PostgreSQL (or initializes defaults) and configures an APScheduler `BackgroundScheduler` instance running the sync job.

### User Request Handling

1. **Routing**: Incoming HTTP requests match routes registered in `backend/app/routers/timesheets.py` or `backend/app/routers/sync.py`.
2. **CORS Validation**: `CORSMiddleware` in `backend/app/main.py` validates incoming request origins against `settings.cors_allowed_origins`.
3. **Session Dependency**: Endpoints inject a database session via `db: Session = Depends(get_db)` (`backend/app/core/db.py`). The generator yields `SessionLocal()` and ensures `db.close()` runs in its `finally` block.
4. **Service Execution**: Handlers delegate directly to service functions (`backend/app/services/timesheet_service.py` or `backend/app/services/sync_service.py`).
5. **Serialization**: Service query results map to Pydantic schemas in `backend/app/schemas/` before JSON transmission.

### Asynchronous Background Trigger

`POST /api/sync/worklogs` launches synchronization asynchronously:
- Spawns a background worker thread via `threading.Thread(target=_run_sync_in_background, daemon=True)`.
- Worker thread opens an independent database session via `db_module.SessionLocal()` and executes `run_sync(db)`.
- Endpoint handler polls PostgreSQL at 10ms intervals (up to 2000ms) until the new `SyncRun` row with status `running` is committed, returning its `run_id` to the caller without waiting for Jira network operations to finish.

---

## Inbound Rate-Limit Tiers and Network Access

The application operates without embedded authentication credentials or user accounts:

| Tier / Boundary | Mechanism | Implementation |
|---|---|---|
| Network Perimeter | Restricted subnet / VPN | Application must only be exposed on an internal corporate network; never expose ports directly to the public internet. |
| Browser Origin | CORS Origin Filtering | `settings.cors_allowed_origins` checks incoming request `Origin`. Wildcards (`*`) are disallowed to prevent cross-site request abuse. |
| Concurrency Control | Single-flight execution | `POST /api/sync/worklogs` inspects the most recent `SyncRun`. If `status == "running"`, the request immediately returns the active run without starting a duplicate worker. |

---

## Database Schema and State Management

PostgreSQL persistence is managed via SQLAlchemy 2.0 declarative models:

| Table | Model File | Purpose | Constraints & Indexes |
|---|---|---|---|
| `issues` | `backend/app/models/issue.py` | Stores synced Jira issue summaries and project keys | Primary key: `id` (Jira issue ID string). Unique index: `key`. Index: `project_key`. |
| `worklogs` | `backend/app/models/worklog.py` | Synced worklog entries with hours and dates | Primary key: `id`. Foreign key: `issue_id` -> `issues.id`. Indexes: `ix_worklogs_work_date`, `ix_worklogs_author_account_id_work_date`, `ix_worklogs_issue_id`. |
| `sync_state` | `backend/app/models/sync_state.py` | Watermark cursor for incremental sync | Singleton constraint: `id = 1` (`ck_sync_state_single_row`). Column: `last_watermark` (nullable tz-aware datetime). |
| `sync_schedule` | `backend/app/models/sync_schedule.py` | Active cron schedule and project key filters | Singleton constraint: `id = 1` (`ck_sync_schedule_single_row`). Columns: `cron_expression`, `project_keys` (CSV string), `updated_at`. |
| `sync_run` | `backend/app/models/sync_run.py` | Historical audit log for sync executions | Primary key: `id` (autoincrement). Columns: `started_at`, `finished_at`, `status`, `worklogs_upserted`, `worklogs_deleted`, `error`, `log_text`. |

For operational details on how state transitions occur during synchronization, see [`async-tasks.md`](async-tasks.md). For feature endpoints consuming these models, see [`features.md`](features.md).
