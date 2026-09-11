# HTTP Clients

Function signatures, base URLs, authentication modes, pagination patterns, and retry mechanisms for outbound HTTP clients.

## JiraClient

The `JiraClient` class in `backend/app/core/jira_http.py` manages all outbound communication with the Jira Cloud REST API v3.

### Configuration and Authentication

- **Base URL**: Defaults to `settings.jira_base_url.rstrip("/")`.
- **Authentication**: HTTP Basic Auth via `httpx.BasicAuth(email, api_token)` using technical user credentials (`settings.jira_email` and `settings.jira_api_token`). Never uses per-user OAuth tokens.
- **Client Lifecycle**: Supports context manager usage (`with JiraClient() as client:`). Internal `httpx.Client` is closed on exit when instantiated by the class.

### Constructor Signature

```python
def __init__(
    self,
    *,
    base_url: str | None = None,
    email: str | None = None,
    api_token: str | None = None,
    max_retries: int | None = None,
    retry_base_seconds: float | None = None,
    client: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> None: ...
```

### Method Signatures

| Method | Upstream Route | Description |
|---|---|---|
| `get_updated_worklog_ids(since_epoch_millis: int) -> tuple[list[dict], int | None]` | `GET /rest/api/3/worklog/updated` | Fetches updated worklog IDs since given timestamp in milliseconds. Paginates via `nextPage` until exhausted. Returns all change items and highest `until` epoch timestamp. |
| `get_deleted_worklog_ids(since_epoch_millis: int) -> list[dict]` | `GET /rest/api/3/worklog/deleted` | Fetches deleted worklog IDs since given timestamp in milliseconds. Paginates via `nextPage`. Stores the latest `until` timestamp on `self.last_deleted_until` and returns changes. |
| `get_worklogs_by_ids(worklog_ids: list[str]) -> list[dict]` | `POST /rest/api/3/worklog/list` | Fetches full worklog objects for up to 1,000 IDs per request. Automatically slices larger ID lists into multiple 1,000-element requests and concatenates the resulting arrays. |
| `get_issue(issue_id: str) -> dict | None` | `GET /rest/api/3/issue/{issue_id}` | Retrieves issue summary and project key (`fields=summary,project`). Returns `None` if Jira responds with HTTP 404 (e.g. issue deleted upstream). |

### Retry and Throttling Policy

Outbound requests handle Jira Cloud rate limiting (HTTP 429) automatically:

1. Checks HTTP response status code for 429.
2. Extracts wait delay from the `Retry-After` header (accepts either integer seconds or HTTP-date format).
3. Computes exponential backoff: `backoff = self.retry_base_seconds * (2 ** attempt)`.
4. Sleeps for `max(backoff, retry_after or 0.0)`.
5. Retries up to `self.max_retries` attempts before raising `httpx.HTTPStatusError`.
6. Non-429 client and server errors trigger immediate `response.raise_for_status()` (except 404 when `allow_404=True`).

### Runnable Usage Example

```python
from app.core.jira_http import JiraClient

with JiraClient() as client:
    changes, until = client.get_updated_worklog_ids(since_epoch_millis=0)
    worklog_ids = [str(c["worklogId"]) for c in changes[:10]]
    worklogs = client.get_worklogs_by_ids(worklog_ids)
```

For information on how `JiraClient` is invoked during synchronization, see [`async-tasks.md`](async-tasks.md). For global error handling conventions, see [`conventions.md`](conventions.md).
