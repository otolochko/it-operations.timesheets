import httpx
import pytest

from app.core.jira_http import JiraClient


def _client(handler, *, retries=2, base=0.25, sleep=lambda _: None):
    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    return JiraClient(
        base_url="https://jira.example.test",
        email="user@example.test",
        api_token="secret",
        max_retries=retries,
        retry_base_seconds=base,
        client=http_client,
        sleep=sleep,
    )


def test_429_retries_and_respects_retry_after() -> None:
    calls = 0
    sleeps = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "1.5"}, request=request)
        return httpx.Response(
            200,
            json={"values": [], "until": 1234, "lastPage": True},
            request=request,
        )

    client = _client(handler, sleep=sleeps.append)
    values, until = client.get_updated_worklog_ids(0)

    assert values == []
    assert until == 1234
    assert calls == 2
    assert sleeps == [1.5]


def test_429_raises_after_max_retries() -> None:
    calls = 0
    sleeps = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, request=request)

    client = _client(handler, retries=2, base=0.25, sleep=sleeps.append)

    with pytest.raises(httpx.HTTPStatusError):
        client.get_deleted_worklog_ids(0)

    assert calls == 3
    assert sleeps == [0.25, 0.5]


def test_transport_error_retries_and_succeeds() -> None:
    calls = 0
    sleeps = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(
            200,
            json={"values": [], "until": 1234, "lastPage": True},
            request=request,
        )

    client = _client(handler, base=0.25, sleep=sleeps.append)
    values, until = client.get_updated_worklog_ids(0)

    assert values == []
    assert until == 1234
    assert calls == 2
    assert sleeps == [0.25]


def test_transport_error_raises_after_max_retries() -> None:
    calls = 0
    sleeps = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectTimeout("connect timed out", request=request)

    client = _client(handler, retries=2, base=0.25, sleep=sleeps.append)

    with pytest.raises(httpx.ConnectTimeout):
        client.get_deleted_worklog_ids(0)

    assert calls == 3
    assert sleeps == [0.25, 0.5]


def test_updated_feed_pages_and_worklog_list_chunks() -> None:
    get_calls = 0
    posted_sizes = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal get_calls
        if request.method == "GET":
            get_calls += 1
            if get_calls == 1:
                return httpx.Response(
                    200,
                    json={
                        "values": [{"worklogId": "1", "updatedTime": 10}],
                        "until": 10,
                        "lastPage": False,
                        "nextPage": "https://jira.example.test/page-two",
                    },
                    request=request,
                )
            return httpx.Response(
                200,
                json={
                    "values": [{"worklogId": "2", "updatedTime": 20}],
                    "until": 20,
                    "lastPage": True,
                },
                request=request,
            )

        ids = __import__("json").loads(request.content)["ids"]
        posted_sizes.append(len(ids))
        return httpx.Response(
            200, json=[{"id": value} for value in ids], request=request
        )

    client = _client(handler)
    changes, until = client.get_updated_worklog_ids(0)
    worklogs = client.get_worklogs_by_ids([str(i) for i in range(2001)])

    assert [item["worklogId"] for item in changes] == ["1", "2"]
    assert until == 20
    assert len(worklogs) == 2001
    assert posted_sizes == [1000, 1000, 1]


def test_get_issue_returns_none_for_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, request=request)

    assert _client(handler).get_issue("missing") is None
