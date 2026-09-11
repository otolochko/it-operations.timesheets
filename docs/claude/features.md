# Features

User-facing features, endpoint routes, service logic, UI components, and behavioral gotchas.

---

## Timesheets

Provides an interactive matrix of Jira worklog hours aggregated by author across daily or weekly periods, summary metric tiles, and issue-level drill-down upon clicking any cell. Operates purely synchronously against PostgreSQL with zero direct Jira calls.

- **Router**: `backend/app/routers/timesheets.py` — endpoints: `GET /api/timesheets` (query params: `from`, `to`, `group=day|week`), `GET /api/timesheets/issues` (query params: `author`, `from`, `to`)
- **Service**: `backend/app/services/timesheet_service.py` — `get_timesheet_grid()` (aggregates author and period totals and computes total hours, author count, issue count, and average hours per author), `get_issue_drilldown()` (queries issue summaries, logged seconds, and worklog counts for a single author and date range)
- **Frontend**: `frontend/src/app/page.tsx` (supported by `frontend/src/components/TimesheetGrid.tsx` and `frontend/src/components/IssueDrilldownPanel.tsx`)
- **Schemas**: `backend/app/schemas/timesheets.py` — `TimesheetCell`, `TimesheetSummary`, `TimesheetGridResponse`, `IssueWorklogEntry`, `IssueDrilldownResponse`
- **Gotchas**:
  - `work_date` is derived from the author's local timezone offset at the time work was logged (`backend/app/core/worklog_time.py`). Normalizing timestamps to UTC shifts calendar dates across midnight boundaries for authors in non-UTC time zones.
  - Week grouping uses PostgreSQL `func.date_trunc('week', Worklog.work_date)`, which follows the ISO standard (weeks start on Monday). There is no configuration option for Sunday or custom week starts.
  - When a user clicks a cell in week grouping mode, `frontend/src/app/page.tsx` expands the single `period_start` date into a 7-day range (`period_start` through `period_start + 6 days`) when querying `GET /api/timesheets/issues`.
  - Date intervals with zero logged worklogs return a 200 OK response with an empty `cells` list and zeroed summary metrics; the frontend renders a "No worklogs in this range." message rather than an error state.

---

## Sync Settings

Controls and monitors background synchronization of Jira Cloud worklogs into PostgreSQL, including manual trigger with live status polling and runtime-configurable cron scheduling. The trigger operation runs asynchronously on a background thread while the API returns immediately.

- **Router**: `backend/app/routers/sync.py` — endpoints: `POST /api/sync/worklogs` (spawns background sync), `GET /api/sync/status` (fetches latest run), `GET /api/sync/schedule` (fetches cron schedule), `PUT /api/sync/schedule` (updates cron schedule and project keys)
- **Service**: `backend/app/services/sync_service.py` (`run_sync()`), `backend/app/services/scheduler.py` (`validate_cron()`, `get_or_create_schedule()`, `reschedule()`, `start_scheduler()`, `get_scheduler()`)
- **Frontend**: `frontend/src/app/sync/page.tsx` (supported by `frontend/src/components/SyncStatusPanel.tsx` and `frontend/src/components/SyncScheduleForm.tsx`)
- **Schemas**: `backend/app/schemas/sync.py` — `SyncRunSummary`, `SyncStatusResponse`, `SyncTriggerResponse`, `SyncScheduleResponse`, `SyncScheduleUpdateRequest`
- **Gotchas**:
  - `POST /api/sync/worklogs` enforces single-flight concurrency: if the latest `SyncRun` is currently marked `running`, it returns the active run immediately and refuses to launch a second run to prevent race conditions on the `sync_state` watermark cursor.
  - The endpoint spawns `run_sync` on a daemon `threading.Thread` rather than using FastAPI's `BackgroundTasks`, because `BackgroundTasks` callbacks only run after the HTTP response has been sent, preventing the endpoint from returning the newly created `run_id`.
  - `PUT /api/sync/schedule` validates cron strings using APScheduler's `CronTrigger.from_crontab()`. Validating with external libraries like `croniter` creates syntax incompatibilities that can accept expressions that crash APScheduler upon startup or rescheduling.
  - Jira Cloud `worklog/updated` and `worklog/deleted` feeds are global across all projects. Sync retrieves changes instance-wide and filters worklogs by configured project keys only after fetching issue metadata.
  - `sync_runs.log_text` is stored in the database but omitted from the `SyncRunSummary` response schema; `frontend/src/components/SyncStatusPanel.tsx` synthesizes a one-line execution summary for display in `LogViewer.tsx`.
  - Incremental sync watermarks advance strictly upon complete transaction success. If an error occurs during sync, database changes are rolled back, `sync_state.last_watermark` remains unchanged, and the failed run is logged.

For architectural flow details, see [`architecture.md`](architecture.md). For asynchronous task execution mechanics, see [`async-tasks.md`](async-tasks.md). For frontend component composition, see [`frontend.md`](frontend.md).
