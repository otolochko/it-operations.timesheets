from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core import db as db_module
from app.core.db import Base, get_db
from app.main import app
from app.models import Issue, Worklog
from fastapi.testclient import TestClient


def _sqlite_date_trunc(unit: str, value: str) -> str:
    """Minimal stand-in for Postgres' date_trunc('week', ...) on SQLite.

    Returns the ISO date (Monday) of the ISO week containing `value`.
    """
    if unit != "week":
        raise NotImplementedError(unit)
    d = date.fromisoformat(value)
    monday = d.fromordinal(d.toordinal() - d.weekday())
    return monday.isoformat()


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _register(dbapi_connection, _):
        dbapi_connection.create_function("date_trunc", 2, _sqlite_date_trunc)

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    with Session(engine, autoflush=False) as session:
        yield session


@pytest.fixture(autouse=True)
def _shutdown_scheduler_after_test():
    # client() triggers the app's real startup hook, which starts a live
    # BackgroundScheduler -- stop it so it doesn't leak into other tests.
    yield
    from app.services import scheduler as scheduler_module

    scheduler = scheduler_module.get_scheduler()
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler_module._scheduler = None


@pytest.fixture
def client(engine, monkeypatch):
    # The app's startup hook (scheduler start -> get_or_create_schedule) opens
    # its own session via app.core.db.SessionLocal, bypassing the get_db
    # dependency override below -- point it at the same migrated engine so
    # TestClient's startup event doesn't hit an empty, unrelated database.
    from sqlalchemy.orm import sessionmaker

    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(
        db_module, "SessionLocal", sessionmaker(bind=engine, autoflush=False, autocommit=False)
    )

    def override_get_db():
        with Session(engine, autoflush=False) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def _issue(db, issue_id, key, summary="Summary"):
    issue = Issue(
        id=issue_id,
        key=key,
        project_key="IN",
        summary=summary,
        updated_at=_dt("2026-01-01T00:00:00"),
    )
    db.add(issue)
    return issue


def _worklog(
    db,
    wl_id,
    issue_id,
    author_account_id,
    author_display_name,
    seconds,
    work_date,
):
    wl = Worklog(
        id=wl_id,
        issue_id=issue_id,
        author_account_id=author_account_id,
        author_display_name=author_display_name,
        time_spent_seconds=seconds,
        started=_dt("2026-01-01T09:00:00"),
        started_utc_offset=0,
        work_date=work_date,
        updated_at=_dt("2026-01-01T09:00:00"),
    )
    db.add(wl)
    return wl


def test_day_grouping_sums_per_author_per_day(client, db):
    _issue(db, "1", "IN-1")
    _worklog(db, "w1", "1", "acct-1", "Ada", 3600, date(2026, 3, 2))
    _worklog(db, "w2", "1", "acct-1", "Ada", 1800, date(2026, 3, 2))
    _worklog(db, "w3", "1", "acct-2", "Bob", 7200, date(2026, 3, 2))
    db.commit()

    resp = client.get(
        "/api/timesheets", params={"from": "2026-03-01", "to": "2026-03-08", "group": "day"}
    )
    assert resp.status_code == 200
    body = resp.json()

    cells = {(c["author_account_id"], c["period_start"]): c["total_seconds"] for c in body["cells"]}
    assert cells[("acct-1", "2026-03-02")] == 5400
    assert cells[("acct-2", "2026-03-02")] == 7200
    assert len(body["cells"]) == 2


def test_week_grouping_sums_across_days_in_same_iso_week(client, db):
    _issue(db, "1", "IN-1")
    # Monday and Wednesday of the same ISO week (2026-03-02 is a Monday).
    _worklog(db, "w1", "1", "acct-1", "Ada", 3600, date(2026, 3, 2))
    _worklog(db, "w2", "1", "acct-1", "Ada", 1800, date(2026, 3, 4))
    db.commit()

    resp = client.get(
        "/api/timesheets", params={"from": "2026-03-01", "to": "2026-03-08", "group": "week"}
    )
    assert resp.status_code == 200
    body = resp.json()

    assert len(body["cells"]) == 1
    cell = body["cells"][0]
    assert cell["period_start"] == "2026-03-02"
    assert cell["total_seconds"] == 5400


def test_summary_metrics_for_multi_author_multi_issue_dataset(client, db):
    _issue(db, "1", "IN-1")
    _issue(db, "2", "IN-2")
    _worklog(db, "w1", "1", "acct-1", "Ada", 3600, date(2026, 3, 2))
    _worklog(db, "w2", "2", "acct-1", "Ada", 3600, date(2026, 3, 3))
    _worklog(db, "w3", "2", "acct-2", "Bob", 7200, date(2026, 3, 3))
    db.commit()

    resp = client.get(
        "/api/timesheets", params={"from": "2026-03-01", "to": "2026-03-08", "group": "day"}
    )
    assert resp.status_code == 200
    summary = resp.json()["summary"]

    assert summary["total_hours"] == pytest.approx(4.0)
    assert summary["author_count"] == 2
    assert summary["issue_count"] == 2
    assert summary["average_hours_per_author"] == pytest.approx(2.0)


def test_empty_range_returns_empty_grid_not_error(client, db):
    _issue(db, "1", "IN-1")
    _worklog(db, "w1", "1", "acct-1", "Ada", 3600, date(2026, 1, 1))
    db.commit()

    resp = client.get(
        "/api/timesheets", params={"from": "2026-06-01", "to": "2026-06-08", "group": "day"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["cells"] == []
    assert body["summary"] == {
        "total_hours": 0.0,
        "author_count": 0,
        "issue_count": 0,
        "average_hours_per_author": 0.0,
    }


def test_to_date_before_from_date_returns_empty_grid_not_error(client, db):
    _issue(db, "1", "IN-1")
    _worklog(db, "w1", "1", "acct-1", "Ada", 3600, date(2026, 3, 2))
    db.commit()

    resp = client.get(
        "/api/timesheets", params={"from": "2026-03-08", "to": "2026-03-01", "group": "day"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["cells"] == []
    assert body["summary"]["author_count"] == 0


def test_drilldown_returns_correct_per_issue_totals(client, db):
    _issue(db, "1", "IN-1", "First issue")
    _issue(db, "2", "IN-2", "Second issue")
    _worklog(db, "w1", "1", "acct-1", "Ada", 3600, date(2026, 3, 2))
    _worklog(db, "w2", "1", "acct-1", "Ada", 1800, date(2026, 3, 3))
    _worklog(db, "w3", "2", "acct-1", "Ada", 900, date(2026, 3, 3))
    _worklog(db, "w4", "2", "acct-2", "Bob", 9999, date(2026, 3, 3))
    db.commit()

    resp = client.get(
        "/api/timesheets/issues",
        params={"author": "acct-1", "from": "2026-03-01", "to": "2026-03-08"},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["author_account_id"] == "acct-1"
    assert body["author_display_name"] == "Ada"
    by_key = {i["issue_key"]: i for i in body["issues"]}
    assert by_key["IN-1"]["total_seconds"] == 5400
    assert by_key["IN-1"]["worklog_count"] == 2
    assert by_key["IN-2"]["total_seconds"] == 900
    assert by_key["IN-2"]["worklog_count"] == 1
    assert len(body["issues"]) == 2


def test_drilldown_empty_for_author_with_no_worklogs(client, db):
    _issue(db, "1", "IN-1")
    _worklog(db, "w1", "1", "acct-1", "Ada", 3600, date(2026, 3, 2))
    db.commit()

    resp = client.get(
        "/api/timesheets/issues",
        params={"author": "acct-unknown", "from": "2026-03-01", "to": "2026-03-08"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["issues"] == []
    assert body["author_display_name"] is None
