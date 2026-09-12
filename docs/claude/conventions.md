# Code Conventions

Global backend coding conventions, response contracts, error handling, rate limiting, and dependency management.

## Response Contract

All backend API routes return JSON payloads matching Pydantic response models defined in `backend/app/schemas/`, except `GET /api/timesheets/export` which returns raw CSV text or binary XLSX file streams.

| Endpoint | Status | Schema |
|---|---|---|
| `GET /api/timesheets` | 200 OK | `TimesheetGridResponse` |
| `GET /api/timesheets/issues` | 200 OK | `IssueDrilldownResponse` |
| `GET /api/timesheets/export` | 200 OK | File download (`text/csv`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`) |
| `POST /api/sync/worklogs` | 200 OK | `SyncTriggerResponse` |
| `GET /api/sync/status` | 200 OK | `SyncStatusResponse` |
| `GET /api/sync/schedule` | 200 OK | `SyncScheduleResponse` |
| `PUT /api/sync/schedule` | 200 OK | `SyncScheduleResponse` |

### Date and Time Formatting

- **Calendar Dates**: Formatted as ISO 8601 strings (`YYYY-MM-DD`). Coerced to and from Python `datetime.date`.
- **Timestamps**: Formatted as ISO 8601 strings with timezone offset (`YYYY-MM-DDTHH:MM:SS+00:00` or `Z`). Coerced to and from timezone-aware Python `datetime.datetime`.

## Error Handling

### HTTP API Errors

Endpoints raise standard `fastapi.HTTPException` with explicit status codes and error messages:

- `400 Bad Request`: Input syntax validation failure, such as invalid cron expressions rejected by `validate_cron()`.
- `422 Unprocessable Entity`: Automatic FastAPI / Pydantic validation failure when parameters fail type checks.
- `500 Internal Server Error`: Server failure, such as background worker initialization exceeding timeout thresholds.

### Service Error Handling

When an uncaught exception occurs during a background sync:
1. Active PostgreSQL transactions are rolled back via `db.rollback()`.
2. The active `SyncRun` record is retrieved, `status` is set to `"failed"`, `error` is assigned `str(exc)`, and the failure is committed.
3. The cursor `sync_state.last_watermark` is **never** updated on failure, ensuring subsequent runs reprocess the failed interval.

```python
try:
    # sync logic
    db.commit()
except Exception as exc:
    db.rollback()
    failed_run = db.get(SyncRun, run_id)
    if failed_run is not None:
        failed_run.status = "failed"
        failed_run.error = str(exc)
        db.commit()
    raise
```

## Outbound Rate Limiting and Retries

Outbound Jira Cloud HTTP requests are managed by `JiraClient` in `backend/app/core/jira_http.py`.

- **Rate Limits**: Jira returns HTTP 429 Too Many Requests when request quotas are exceeded.
- **Retry Logic**: `_request` retries 429 responses up to `settings.jira_max_retries` (default 5).
- **Backoff Calculation**: Retries sleep for the greater of exponential backoff or the server-provided `Retry-After` header:
  ```python
  backoff = self.retry_base_seconds * (2 ** attempt)
  retry_after = self._retry_after_seconds(response)
  self._sleep(max(backoff, retry_after or 0.0))
  ```
- **Terminal Failures**: Non-429 client and server errors raise `httpx.HTTPStatusError` immediately (unless `allow_404=True` is explicitly passed).

## Pagination Patterns

### Jira Change Feed Pagination

The Jira `worklog/updated` and `worklog/deleted` endpoints return paginated change batches:

- Paging continues using the returned `nextPage` URL until `lastPage` is `True` or `nextPage` is absent.
- The highest `until` epoch timestamp across all returned pages is tracked to determine the new watermark cursor.

### Jira Bulk Worklog Retrieval

The `/rest/api/3/worklog/list` endpoint accepts an array of worklog IDs:

- `JiraClient.get_worklogs_by_ids()` slices requests into chunks of at most 1,000 IDs per call.
- Aggregated results are combined into a single list of worklog payloads.

### Database Query Bounds

Timesheet queries do not paginate via cursor or page number. All records are bounded by the `from` and `to` date interval and grouped in SQL.

## Timeouts

- User-facing read requests execute direct SQL queries and return synchronously.
- Heavy synchronization tasks run out-of-band via background threads or APScheduler, preventing gateway and proxy timeouts.
- Outbound Jira requests rely on HTTP client timeouts; transient stalls are caught and retried per the backoff configuration.

## Dry-Run Policy

The application does not expose dry-run modes over the API. Data synchronization is idempotent:
- Issue entities are upserted by primary key `id`.
- Worklog entities are upserted by primary key `id`.
- Deletions remove worklogs matching Jira change IDs.
- Rerunning synchronization over any previously synced time window is safe.

## Dependency Policy

- All Python package dependencies in `backend/requirements.txt` must be pinned to exact version numbers (`package==x.y.z`).
- **Never** use floating version ranges (`>=`, `~=`).
- Cron syntax validation **must** use APScheduler's `CronTrigger.from_crontab()`. **Never** use `croniter` for validation; syntax differences between parsers can accept strings that crash APScheduler at runtime.

For related architectural patterns, see [`architecture.md`](architecture.md). For HTTP client method signatures, see [`api-clients.md`](api-clients.md). For background scheduler details, see [`async-tasks.md`](async-tasks.md).
