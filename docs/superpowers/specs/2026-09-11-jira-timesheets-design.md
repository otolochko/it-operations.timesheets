# Jira Timesheets — Design Spec

Date: 2026-09-11

## Problem

Internal tool to monitor where 800+ people log time in Jira Cloud: daily/weekly
grid of logged hours per author, drill-down per issue, and summary metrics. No
existing marketplace app fits internal needs closely enough; building a small
self-hosted tool instead.

## Constraints / decisions

- Jira Cloud only (REST API v3, bulk worklog endpoints).
- Single technical Jira user/token for sync — not per-user OAuth.
- No authentication in the app itself — deployed on a restricted internal network.
- Issue/project scope is fixed via backend configuration (project keys / JQL
  filter), not chosen ad hoc in the UI.
- Sync frequency is configurable (cron-style schedule), in addition to a manual
  "Sync now" trigger.
- Self-hosted web app (Docker Compose), not a Jira Marketplace app.

## Architecture

```
Jira Cloud --(bulk worklog API, background job)--> PostgreSQL (issues, worklogs, sync_state)
                                                          |
                                Next.js UI <--(indexed SQL)--+<-- FastAPI
```

- **Sync job**: runs on the configured schedule (cron expression, editable via
  UI/API) plus on-demand via "Sync now". Reads the watermark from
  `sync_state`, pages `worklog/updated` / `worklog/deleted` since that
  watermark for the fixed project scope, batch-fetches full worklog objects
  via `worklog/list` (≤1000 ids/call), upserts/deletes rows in `worklogs`
  and `issues`, then advances the watermark — **only on full success**, so a
  failed run can simply be retried (idempotent, no partial watermark
  advancement).
- **Read path**: `GET /api/timesheets` runs a single indexed SQL query against
  `worklogs` for the fixed project scope + requested date range, aggregated
  author × period (day/week) in the backend. No per-issue Jira calls on any
  user-facing request path — this is a hard invariant.

## Data model (PostgreSQL)

- **`issues`**: `id` (Jira issue id, PK), `key`, `project_key`, `summary`,
  `updated_at`. Lightweight metadata cache, refreshed during sync.
- **`worklogs`**: `id` (Jira worklog id, PK), `issue_id` (FK → issues),
  `author_account_id`, `author_display_name`, `time_spent_seconds`,
  `started` (timestamptz, original value), `started_utc_offset` (stored
  separately), `work_date` (date, computed from the worklog's own local
  offset — never from a UTC-normalized timestamp), `updated_at`.
  Indexes: `(work_date)`, `(author_account_id, work_date)`, `(issue_id)`.
- **`sync_state`**: single-row watermark for the incremental sync cursor.
- **`sync_schedule`**: single-row cron expression + scope configuration
  consumed by the scheduler.

**Invariant carried over from the prior project this was extracted from:**
`work_date` must be derived from the worklog's own local UTC offset, identically
whether the `Worklog` is built from raw Jira JSON (sync time) or from a stored
DB row (query time). Normalizing to UTC first shifts the day for authors in
different time zones and must never happen.

## Backend API

- `GET /api/timesheets?from=&to=&group=day|week` — author × period grid +
  summary metrics (total hours, author count, issue count, averages).
- `GET /api/timesheets/issues?author=&from=&to=` — drill-down: worklogs for a
  given author/period, grouped by issue.
- `POST /api/sync/worklogs` — manual sync trigger (async job).
- `GET /api/sync/status` — status of the last/current sync run.
- `GET /api/sync/schedule` / `PUT /api/sync/schedule` — view/edit the cron
  schedule and scope configuration.

## Error handling

- Jira `429` → retry with backoff (configurable `JIRA_MAX_RETRIES` /
  `JIRA_RETRY_BASE_SECONDS`).
- A sync run that fails mid-way does not advance the watermark; re-running it
  is always safe.
- Empty scope or date range with no data → render an empty grid, not an error.

## Stack

- **Backend**: FastAPI, SQLAlchemy, Alembic, PostgreSQL.
- **Frontend**: Next.js + TypeScript + Tailwind CSS 3, using the design system
  below (CSS custom properties for all colors, dark mode via `data-theme` on
  `<html>`, no hardcoded hex/rgb in component files).
- **Deployment**: Docker Compose (backend, frontend, PostgreSQL).
- **Auth**: none — internal network only.
- **Jira access**: single technical user/API token, backend-only, never
  logged or exposed to the frontend.

### Frontend design system (summary — full spec supplied by user)

- Tokens defined as CSS custom properties in `src/app/globals.css`, mapped in
  `tailwind.config.ts`, mirrored in `src/lib/theme/tokens.ts` for JS use.
- Core palette: `--accent`, `--accent-hover`, `--success`, `--danger`,
  `--warning`, `--bg`, `--card`, `--field-bg`, `--border`, `--text-primary`,
  `--text-muted`, `--surface-raised`, `--surface-overlay`, `--brand-2`.
- Separate fixed `--log-*` token family for the log/terminal viewer only
  (`LogViewer.tsx`), used to show sync run status/logs.
- Typography: DM Sans (UI), IBM Plex Mono (code/logs).
- Shared components: `Buttons.tsx` (Primary/Secondary/Danger), `FormField.tsx`,
  `PanelCard.tsx`, `StatusBadge.tsx` (info/success/danger), `NavSidebar.tsx`,
  `LogViewer.tsx`.
- Pages: `TimesheetsPage` (author × date/week grid, day/week toggle, date
  range filter, summary metrics, click-through drill-down) and
  `SyncSettingsPage` (last sync status via `LogViewer`/`StatusBadge`, "Sync
  now" button, schedule editor).
- Rule: no hardcoded hex/rgb in `.tsx` files — always a CSS variable or
  Tailwind token class. `--log-*` tokens confined to the log viewer;
  Google-button tokens are not applicable here (no OAuth login in this app).

## Testing

- Backend (pytest): sync upsert/delete idempotency, watermark advancement
  logic, `work_date` offset computation from both raw Jira JSON and DB rows,
  timesheet aggregation correctness.
- Frontend (vitest): grid rendering, drill-down interaction, sync status
  display.

## Out of scope

- Per-user OAuth / app-level authentication.
- Ad hoc JQL entry in the UI (scope is fixed server-side configuration).
- Anything beyond Timesheets (capacity planning, burndown, days-off — not
  ported from the prior project this was extracted from).
