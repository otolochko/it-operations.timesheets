from copy import deepcopy
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import Base
from app.models import Issue, SyncRun, SyncState, Worklog
from app.services.sync_service import get_or_create_schedule, run_sync


class FakeJiraClient:
    def __init__(
        self,
        worklogs=None,
        issues=None,
        deleted=None,
        until=1_800_000_000_000,
        fail_issue_id=None,
        jql_matches=None,
    ):
        self.worklogs = worklogs or []
        self.issues = issues or {}
        self.deleted = deleted or []
        self.until = until
        self.last_deleted_until = until
        self.fail_issue_id = fail_issue_id
        self.issue_calls = []
        self.jql_matches = jql_matches
        self.jql_calls = []

    def get_updated_worklog_ids(self, since, *, on_page=None):
        return [
            {"worklogId": item["id"], "updatedTime": self.until}
            for item in self.worklogs
        ], self.until

    def get_deleted_worklog_ids(self, since, *, on_page=None):
        return deepcopy(self.deleted)

    def get_worklogs_by_ids(self, ids, *, on_page=None):
        wanted = set(ids)
        return deepcopy([item for item in self.worklogs if item["id"] in wanted])

    def get_issue(self, issue_id):
        self.issue_calls.append(issue_id)
        if issue_id == self.fail_issue_id:
            raise RuntimeError("simulated Jira issue failure")
        return deepcopy(self.issues.get(issue_id))

    def search_issue_ids(self, jql, *, on_page=None):
        self.jql_calls.append(jql)
        return set(self.jql_matches or set())


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False) as session:
        yield session
    engine.dispose()


@pytest.fixture(autouse=True)
def project_scope(monkeypatch):
    monkeypatch.setattr(settings, "jira_project_keys_raw", "IN")


def issue(issue_id="100", key="IN-1", project="IN"):
    return {
        "id": issue_id,
        "key": key,
        "fields": {"summary": f"Issue {key}", "project": {"key": project}},
    }


def worklog(
    worklog_id="500",
    issue_id="100",
    issue_key="IN-1",
    seconds=3600,
):
    return {
        "id": worklog_id,
        "issueId": issue_id,
        "issueKey": issue_key,
        "author": {"accountId": "acct-1", "displayName": "Ada"},
        "timeSpentSeconds": seconds,
        "started": "2026-09-11T08:30:00.000+0200",
        "updated": "2026-09-11T09:00:00.000+0000",
    }


def test_progress_reflects_completion(db: Session) -> None:
    result = run_sync(db, FakeJiraClient([worklog()], {"100": issue()}))

    assert result.progress_phase == "Completed"
    assert result.progress_current == result.progress_total


def test_upsert_is_idempotent(db: Session) -> None:
    fake = FakeJiraClient([worklog()], {"100": issue()})

    first = run_sync(db, fake)
    first_values = db.scalars(select(Worklog)).all()
    second = run_sync(db, fake)
    second_values = db.scalars(select(Worklog)).all()

    assert first.status == second.status == "success"
    assert len(first_values) == len(second_values) == 1
    assert second_values[0].id == "500"
    assert second_values[0].time_spent_seconds == 3600
    assert db.scalar(select(Issue).where(Issue.id == "100")) is not None


def test_existing_worklog_is_updated_in_place(db: Session) -> None:
    initial = FakeJiraClient([worklog(seconds=1800)], {"100": issue()})
    run_sync(db, initial)

    changed = FakeJiraClient([worklog(seconds=7200)], {"100": issue()})
    run_sync(db, changed)

    rows = db.scalars(select(Worklog)).all()
    assert len(rows) == 1
    assert rows[0].time_spent_seconds == 7200


def test_deleted_worklog_is_removed(db: Session) -> None:
    run_sync(db, FakeJiraClient([worklog()], {"100": issue()}, until=1000))
    deletion = FakeJiraClient(
        worklogs=[],
        issues={},
        deleted=[{"worklogId": "500", "updatedTime": 2000}],
        until=2000,
    )

    result = run_sync(db, deletion)

    assert db.get(Worklog, "500") is None
    assert result.worklogs_deleted == 1


def test_failure_rolls_back_and_retry_is_safe(db: Session) -> None:
    old_watermark = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.add(SyncState(id=1, last_watermark=old_watermark))
    db.commit()

    data = [worklog("500", "100", "IN-1"), worklog("501", "101", "IN-2")]
    issues = {"100": issue(), "101": issue("101", "IN-2")}
    failing = FakeJiraClient(data, issues, fail_issue_id="101")

    with pytest.raises(RuntimeError, match="simulated Jira issue failure"):
        run_sync(db, failing)

    state = db.get(SyncState, 1)
    assert state.last_watermark == old_watermark.replace(tzinfo=None)
    assert db.scalars(select(Worklog)).all() == []
    failed = db.scalars(select(SyncRun).order_by(SyncRun.id.desc())).first()
    assert failed.status == "failed"
    assert failed.error

    success = run_sync(db, FakeJiraClient(data, issues))
    assert success.status == "success"
    assert {row.id for row in db.scalars(select(Worklog))} == {"500", "501"}


def test_success_advances_watermark(db: Session) -> None:
    expected_millis = 1_800_000_123_456
    run_sync(
        db,
        FakeJiraClient([worklog()], {"100": issue()}, until=expected_millis),
    )

    expected = datetime.fromtimestamp(expected_millis / 1000, tz=timezone.utc)
    assert db.get(SyncState, 1).last_watermark == expected.replace(tzinfo=None)


def test_project_scope_excludes_out_of_scope_worklogs(db: Session) -> None:
    data = [
        worklog("500", "100", "IN-1"),
        worklog("600", "200", "OUT-1"),
    ]
    issues = {
        "100": issue(),
        "200": issue("200", "OUT-1", "OUT"),
    }
    fake = FakeJiraClient(data, issues)

    result = run_sync(db, fake)

    assert {row.id for row in db.scalars(select(Worklog))} == {"500"}
    assert result.worklogs_upserted == 1
    assert fake.issue_calls == ["100"]


def test_empty_project_scope_allows_all_projects(db: Session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "jira_project_keys_raw", "")
    out = worklog("600", "200", "OUT-1")

    run_sync(db, FakeJiraClient([out], {"200": issue("200", "OUT-1", "OUT")}))

    assert db.get(Worklog, "600") is not None


def test_jql_filter_replaces_project_scope(db: Session) -> None:
    schedule = get_or_create_schedule(db)
    schedule.jql_filter = "labels = keep"
    db.commit()

    data = [
        worklog("500", "100", "IN-1"),
        worklog("600", "200", "OUT-1"),
    ]
    issues = {
        "100": issue(),
        "200": issue("200", "OUT-1", "OUT"),
    }
    fake = FakeJiraClient(data, issues, jql_matches={"100"})

    result = run_sync(db, fake)

    assert fake.jql_calls == ["labels = keep"]
    assert {row.id for row in db.scalars(select(Worklog))} == {"500"}
    assert result.worklogs_upserted == 1
    assert fake.issue_calls == ["100"]
