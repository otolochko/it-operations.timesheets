"""Small synchronous client for the Jira Cloud worklog APIs."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from app.core.config import settings


class JiraClient:
    """Jira Cloud REST client using one technical user's credentials."""

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
    ) -> None:
        self.base_url = (base_url or settings.jira_base_url).rstrip("/")
        self.max_retries = (
            settings.jira_max_retries if max_retries is None else max_retries
        )
        self.retry_base_seconds = (
            settings.jira_retry_base_seconds
            if retry_base_seconds is None
            else retry_base_seconds
        )
        self._sleep = sleep
        self._owns_client = client is None
        self._client = client or httpx.Client(
            auth=httpx.BasicAuth(
                email or settings.jira_email,
                api_token or settings.jira_api_token,
            )
        )
        self.last_deleted_until: int | None = None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> JiraClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @staticmethod
    def _retry_after_seconds(response: httpx.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return None

    def _request(
        self, method: str, url: str, *, allow_404: bool = False, **kwargs: Any
    ) -> httpx.Response:
        for attempt in range(self.max_retries + 1):
            response = self._client.request(method, url, **kwargs)
            if response.status_code != 429:
                if allow_404 and response.status_code == 404:
                    return response
                response.raise_for_status()
                return response
            if attempt == self.max_retries:
                response.raise_for_status()

            backoff = self.retry_base_seconds * (2**attempt)
            retry_after = self._retry_after_seconds(response)
            self._sleep(max(backoff, retry_after or 0.0))

        raise RuntimeError("unreachable")

    def _get_change_pages(
        self,
        endpoint: str,
        since_epoch_millis: int,
        *,
        on_page: Callable[[int, int], None] | None = None,
    ) -> tuple[list[dict], int | None]:
        url = f"{self.base_url}/rest/api/3/worklog/{endpoint}"
        params: dict[str, int] | None = {"since": since_epoch_millis}
        values: list[dict] = []
        max_until: int | None = None
        page = 0

        while True:
            response = self._request("GET", url, params=params)
            payload = response.json()
            values.extend(payload.get("values", []))
            page += 1
            if on_page is not None:
                on_page(page, len(values))
            until = payload.get("until")
            if until is not None:
                until = int(until)
                max_until = until if max_until is None else max(max_until, until)

            next_page = payload.get("nextPage")
            if payload.get("lastPage", next_page is None) or not next_page:
                break
            url = next_page
            params = None

        return values, max_until

    def get_updated_worklog_ids(
        self,
        since_epoch_millis: int,
        *,
        on_page: Callable[[int, int], None] | None = None,
    ) -> tuple[list[dict], int | None]:
        return self._get_change_pages("updated", since_epoch_millis, on_page=on_page)

    def get_deleted_worklog_ids(
        self,
        since_epoch_millis: int,
        *,
        on_page: Callable[[int, int], None] | None = None,
    ) -> list[dict]:
        values, self.last_deleted_until = self._get_change_pages(
            "deleted", since_epoch_millis, on_page=on_page
        )
        return values

    def get_worklogs_by_ids(
        self,
        worklog_ids: list[str],
        *,
        on_page: Callable[[int, int], None] | None = None,
    ) -> list[dict]:
        worklogs: list[dict] = []
        url = f"{self.base_url}/rest/api/3/worklog/list"
        page = 0
        for start in range(0, len(worklog_ids), 1000):
            response = self._request(
                "POST", url, json={"ids": worklog_ids[start : start + 1000]}
            )
            worklogs.extend(response.json())
            page += 1
            if on_page is not None:
                on_page(page, len(worklogs))
        return worklogs

    def get_issue(self, issue_id: str) -> dict | None:
        url = f"{self.base_url}/rest/api/3/issue/{issue_id}"
        response = self._request(
            "GET",
            url,
            allow_404=True,
            params={"fields": "summary,project"},
        )
        if response.status_code == 404:
            return None
        return response.json()

    def search_issue_ids(
        self, jql: str, *, on_page: Callable[[int, int], None] | None = None
    ) -> set[str]:
        url = f"{self.base_url}/rest/api/3/search/jql"
        issue_ids: set[str] = set()
        page = 0
        next_page_token: str | None = None

        while True:
            body: dict[str, Any] = {"jql": jql, "fields": ["id"], "maxResults": 5000}
            if next_page_token is not None:
                body["nextPageToken"] = next_page_token
            response = self._request("POST", url, json=body)
            payload = response.json()
            issue_ids.update(str(issue["id"]) for issue in payload.get("issues", []))
            page += 1
            if on_page is not None:
                on_page(page, len(issue_ids))

            next_page_token = payload.get("nextPageToken")
            if not next_page_token:
                break

        return issue_ids

    def validate_jql(self, jql: str) -> None:
        url = f"{self.base_url}/rest/api/3/search/jql"
        response = self._client.post(
            url, json={"jql": jql, "fields": [], "maxResults": 1}
        )
        if response.status_code == 400:
            errors = response.json().get("errorMessages") or ["Invalid JQL"]
            raise ValueError("; ".join(errors))
        response.raise_for_status()
