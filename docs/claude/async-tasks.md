# Background Tasks and Scheduling

Asynchronous synchronization workflows, task persistence, watermark cursor state machine, and scheduler lifecycle.

## Task Execution Overview

Worklog synchronization from Jira Cloud runs out-of-band to keep user-facing read endpoints fast and isolated from external network stalls:

```
Trigger (Cron or POST /api/sync/worklogs)
   │
   ▼
Task Runner (APScheduler or background Thread)
   │
   ▼
run_sync(db) ──► Record SyncRun("running")
   │
   ├──► Ingest changes via JiraClient
   ├──► Upsert issues and worklogs in PostgreSQL
   │
   ▼
Outcome?
   ├─► SUCCESS:   Update sync_state.last_watermark, commit, mark SyncRun("success")
   ├─► CANCELLED: Rollback uncommitted DB changes, leave watermark untouched, mark SyncRun("cancelled")
   └─► FAILED:    Rollback DB changes, leave watermark untouched, mark SyncRun("failed")
```

## Execution Modes

| Mode | Trigger Mechanism | Threading & Session Lifecycle |
|---|---|---|
| Scheduled | APScheduler `BackgroundScheduler` (`JOB_ID = "sync_job"`) | Executes `_run_sync_job()` on an APScheduler worker thread. Opens and closes a dedicated `SessionLocal()` session. |
| Manual | `POST /api/sync/worklogs` | Spawns a daemon thread via `threading.Thread(target=_run_sync_in_background, daemon=True)`. Handler polls for up to 2000ms until the new `SyncRun` row is committed, returning its ID immediately. |
| Cancellation | `POST /api/sync/worklogs/cancel` | Sets `cancel_requested = True` on the running `SyncRun` row. The worker detects the flag cooperatively at its next checkpoint. |

## Concurrency Guard

The database maintains a single watermark cursor in the `sync_state` table:

- `POST /api/sync/worklogs` inspects the most recent `SyncRun` record.
- If the latest run has `status == "running"`, the endpoint immediately returns the existing run metadata and refuses to start a duplicate worker.
- **Never** allow concurrent sync executions; parallel runs race on the single-row `sync_state` cursor and issue redundant Jira API calls.

## Task Store (`sync_runs` Table)

Execution history is recorded in `sync_runs` (`backend/app/models/sync_run.py`):

- `id`: Integer primary key (autoincrement).
- `started_at`: UTC timestamp when execution began.
- `finished_at`: UTC timestamp when execution finished (null while running).
- `status`: Execution state (`"running"`, `"success"`, `"failed"`, or `"cancelled"`).
- `worklogs_upserted`: Number of worklogs inserted or updated in PostgreSQL.
- `worklogs_deleted`: Number of worklogs deleted matching Jira change events.
- `error`: Exception message if status is `"failed"`.
- `log_text`: Sequential execution log text updated and committed incrementally as sync progresses.
- `cancel_requested`: Boolean flag set by `POST /api/sync/worklogs/cancel` to request cooperative cancellation.
- `progress_phase`: Current sync phase (nullable string, e.g. `"fetching_changes"`, `"fetching_worklogs"`, `"fetching_issues"`, `"processing_worklogs"`).
- `progress_current`: Current count of processed units in the active phase.
- `progress_total`: Total count of units in the active phase (null if indeterminate).

The initial `"running"` status is committed immediately so that status polling endpoints (`GET /api/sync/status`) can observe running tasks.

## Cooperative Cancellation

Sync cancellation operates cooperatively:

1. `POST /api/sync/worklogs/cancel` marks `SyncRun.cancel_requested = True` on the active run.
2. The sync worker (`run_sync`) checks this flag at each phase boundary and after each page batch via its `_progress()` helper.
3. When cancellation is detected, `run_sync` raises `SyncCancelled`, rolls back uncommitted changes, marks the run as `"cancelled"`, leaves `sync_state.last_watermark` untouched, and commits the terminal state.

## Watermark State Machine (`sync_state` Table)

Incremental sync tracking relies on the `sync_state` singleton table (`backend/app/models/sync_state.py`):

1. **Initial Sync**: If `sync_state` is empty, row `id=1` is created with `last_watermark = None`. The sync requests changes since epoch 0.
2. **Incremental Sync**: Subsequent runs query changes where timestamp is greater than `_epoch_millis(state.last_watermark)`.
3. **Cursor Advancement**: `state.last_watermark` is updated to the maximum `until` timestamp returned by Jira's change pages.
4. **Atomicity**: The watermark advances **only** when all issue and worklog upserts commit successfully.
5. **Rollback Behavior**: If any exception or cancellation occurs during synchronization, `db.rollback()` reverts all worklog modifications. The watermark remains at its previous value, ensuring future runs re-ingest the uncommitted interval.

## Dynamic Scheduling (`sync_schedule` Table)

Scheduler parameters are persisted in the `sync_schedule` singleton table (`backend/app/models/sync_schedule.py`):

- **Cron Expression**: 5-field cron string defining the sync schedule.
- **Project Filter**: Comma-separated list of Jira project keys to ingest.
- **JQL Filter**: Optional custom JQL query string (`jql_filter`). When set, Jira issue IDs are resolved via `JiraClient.search_issue_ids` and override the project-key filter.
- **Validation**: `validate_cron()` in `backend/app/services/scheduler.py` validates cron input using `CronTrigger.from_crontab()`. JQL expressions are validated against Jira via `JiraClient.validate_jql()` before persisting.
- **Runtime Updates**: When `PUT /api/sync/schedule` is called, changes are saved to PostgreSQL and `reschedule(scheduler, cron_expression)` reconfigures the running `BackgroundScheduler` in memory without restarting the process.

## Client Polling Contract

The frontend does not use Server-Sent Events (SSE) or WebSockets:

- `frontend/src/components/SyncStatusPanel.tsx` fetches `GET /api/sync/status`.
- When `is_running` is `true`, a 2000ms polling timer is active.
- Polling stops automatically once `is_running` evaluates to `false`.

## Process Restart and Recovery

- **Process Restart**: FastAPI lifespan startup in `backend/app/main.py` invokes `start_scheduler()`, reading the persisted schedule from `sync_schedule` and initializing the background job.
- **Interrupted Sync Recovery**: If the server crashes or restarts during an active run, the interrupted worker thread terminates. Because the watermark was not committed, the next scheduled or manual run safely restarts from the previous watermark without data loss or corruption.

For service-level sync orchestration details, see [`features.md`](features.md). For Jira HTTP methods used during sync, see [`api-clients.md`](api-clients.md).
