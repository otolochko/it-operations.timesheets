# Features

User-facing features, endpoint routes, service logic, UI components, and behavioral gotchas.

---

## Timesheets

Provides an interactive matrix of Jira worklog hours aggregated by author across daily or weekly periods, summary metric tiles, and issue-level drill-down upon clicking any cell. Operates purely synchronously against PostgreSQL with zero direct Jira calls.

- **Router**: `backend/app/routers/timesheets.py` — endpoints: `GET /api/timesheets` (query params: `from`, `to`, `group=day|week`), `GET /api/timesheets/issues` (query params: `author`, `from`, `to`), `GET /api/timesheets/export` (query params: `from`, `to`, `group=day|week`, `format=csv|xlsx`, `dataset=matrix|raw|issues`)
- **Service**: `backend/app/services/timesheet_service.py` — `get_timesheet_grid()` (aggregates author and period totals and computes total hours, author count, issue count, and average hours per author), `get_issue_drilldown()` (queries issue summaries, logged seconds, and worklog counts for a single author and date range), `get_all_issue_totals()` (queries all-authors per-issue totals across date range); `backend/app/services/export_service.py` — `build_csv()`, `build_xlsx()` (shapes aggregated timesheet and issue totals into CSV text or styled multi-sheet XLSX workbooks)
- **Frontend**: `frontend/src/app/page.tsx` (supported by `frontend/src/components/TimesheetGrid.tsx` and `frontend/src/components/IssueDrilldownPanel.tsx`)
- **Schemas**: `backend/app/schemas/timesheets.py` — `TimesheetCell`, `TimesheetSummary`, `TimesheetGridResponse`, `IssueWorklogEntry`, `IssueDrilldownResponse`
- **Gotchas**:
  - `work_date` is derived from the author's local timezone offset at the time work was logged (`backend/app/core/worklog_time.py`). Normalizing timestamps to UTC shifts calendar dates across midnight boundaries for authors in non-UTC time zones.
  - Week grouping uses PostgreSQL `func.date_trunc('week', Worklog.work_date)`, which follows the ISO standard (weeks start on Monday). There is no configuration option for Sunday or custom week starts.
  - When a user clicks a cell in week grouping mode, `frontend/src/app/page.tsx` expands the single `period_start` date into a 7-day range (`period_start` through `period_start + 6 days`) when querying `GET /api/timesheets/issues`.
  - Date intervals with zero logged worklogs return a 200 OK response with an empty `cells` list and zeroed summary metrics; the frontend renders a "No worklogs in this range." message rather than an error state.
  - Exported string cells must be sanitized against spreadsheet formula injection via `_safe_cell()` / `_safe_row()` in `backend/app/services/export_service.py`. Jira issue summaries, display names, and project/issue keys are attacker-controllable; any string starting with `=`, `+`, `-`, `@`, `\t`, or `\r` is prefixed with an apostrophe (`'`). Numeric cells pass through untouched so Excel can sum them. Any newly added exported column must route its values through `_safe_cell` or `_safe_row`.
  - The `dataset` query parameter (`matrix`, `raw`, `issues`) is only applicable to CSV exports; Excel exports (`format=xlsx`) always write all three datasets as separate workbook sheets (`Matrix`, `Raw`, `Issues`).
  - An empty date range returns a valid header-only file with HTTP 200 rather than an error, consistent with the empty-grid behavior of `GET /api/timesheets`.
  - CSV exports offer both `matrix` and `raw` datasets: `matrix` mirrors the on-screen author-by-period grid with row and column totals, whereas `raw` provides normalized long-format records (`Author, Account ID, Period, Hours`) suited for spreadsheet pivot tables.

---

## Sync Settings

Controls and monitors background synchronization of Jira Cloud worklogs into PostgreSQL, including manual trigger with live status polling and runtime-configurable cron scheduling. The trigger operation runs asynchronously on a background thread while the API returns immediately.

- **Router**: `backend/app/routers/sync.py` — endpoints: `POST /api/sync/worklogs` (spawns background sync), `POST /api/sync/worklogs/cancel` (requests cooperative cancellation of the in-progress run), `GET /api/sync/status` (fetches latest run), `GET /api/sync/schedule` (fetches cron schedule), `PUT /api/sync/schedule` (updates cron schedule, project keys, and JQL filter)
- **Service**: `backend/app/services/sync_service.py` (`run_sync()`, `get_or_create_schedule()`, `is_sync_running()`, `SyncCancelled`), `backend/app/services/scheduler.py` (`validate_cron()`, `reschedule()`, `start_scheduler()`, `get_scheduler()`)
- **Frontend**: `frontend/src/app/sync/page.tsx` (supported by `frontend/src/components/SyncStatusPanel.tsx` and `frontend/src/components/SyncScheduleForm.tsx`)
- **Schemas**: `backend/app/schemas/sync.py` — `SyncRunSummary`, `SyncStatusResponse`, `SyncTriggerResponse`, `SyncScheduleResponse`, `SyncScheduleUpdateRequest`
- **Gotchas**:
  - `POST /api/sync/worklogs` enforces single-flight concurrency: if the latest `SyncRun` is currently marked `running`, it returns the active run immediately and refuses to launch a second run to prevent race conditions on the `sync_state` watermark cursor. The cron path (`scheduler.py`'s `_run_sync_job`) enforces the same via `is_sync_running()`, silently skipping its fire instead of racing a manual trigger (or a prior cron fire orphaned by a backend restart mid-run).
  - The endpoint spawns `run_sync` on a daemon `threading.Thread` rather than using FastAPI's `BackgroundTasks`, because `BackgroundTasks` callbacks only run after the HTTP response has been sent, preventing the endpoint from returning the newly created `run_id`.
  - Cancellation is cooperative, not preemptive: `POST /api/sync/worklogs/cancel` only sets `SyncRun.cancel_requested`; `run_sync`'s `_progress()` helper checks it after every checkpoint commit (thanks to SQLAlchemy's `expire_on_commit` default re-reading the row) and raises `SyncCancelled`, so the run stops shortly after the flag is set, not instantly — the current in-flight Jira HTTP call still completes first. A cancelled run rolls back any uncommitted work and is marked `status="cancelled"`, leaving `sync_state.last_watermark` untouched like a failed run.
  - `PUT /api/sync/schedule` validates cron strings using APScheduler's `CronTrigger.from_crontab()`. Validating with external libraries like `croniter` creates syntax incompatibilities that can accept expressions that crash APScheduler upon startup or rescheduling.
  - `PUT /api/sync/schedule` also validates a non-empty `jql_filter` with a live Jira call (`JiraClient.validate_jql`, `/rest/api/3/search/jql` with `maxResults=1` — Jira rejects `maxResults=0`) so a syntactically invalid JQL clause is rejected with `400` at save time instead of failing every future sync run.
  - Jira Cloud `worklog/updated` and `worklog/deleted` feeds are global across all projects. Sync retrieves changes instance-wide, then scopes worklogs to `SyncSchedule.jql_filter` (resolved once per run via `JiraClient.search_issue_ids`) when set, or `SyncSchedule.project_keys` otherwise — a non-empty `jql_filter` fully replaces the project-key filter for that run.
  - `sync_runs.log_text` is appended to and committed incrementally during a run (via `_append_log`, including per-page progress for the worklog change feed and JQL search), so `frontend/src/components/SyncStatusPanel.tsx`'s 2s polling shows live progress in `LogViewer.tsx`, not just a final summary.
  - Issue metadata (key/summary/project) is only fetched from Jira for issues not already present in the local `issues` table — an issue synced in a prior run is assumed unchanged and skipped. New issues are fetched in batches via `JiraClient.get_issues_by_ids` (`id in (...)` search, up to 500 per request) rather than one `GET /issue/{id}` per issue, since a large first sync can touch thousands of unique issues.
  - Incremental sync watermarks advance strictly upon complete transaction success. If an error occurs during sync, database changes are rolled back, `sync_state.last_watermark` remains unchanged, and the failed run is logged.

For architectural flow details, see [`architecture.md`](architecture.md). For asynchronous task execution mechanics, see [`async-tasks.md`](async-tasks.md). For frontend component composition, see [`frontend.md`](frontend.md).
