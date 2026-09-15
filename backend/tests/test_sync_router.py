"""Tests for the sync control API and scheduler wiring."""

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.core import db as db_module
from app.core.jira_http import JiraClient
from app.models import SyncRun
from app.routers import sync as sync_router
from app.services import scheduler as scheduler_module
from apscheduler.triggers.cron import CronTrigger
from tests.conftest import build_sqlite_engine
from tests.asgi_client import ASGITestClient


@pytest.fixture(autouse=True)
def shared_sqlite_engine(monkeypatch):
    """Point app.core.db at a single shared-connection sqlite engine.

    The router and scheduler open their own sessions on background threads
    via `db_module.SessionLocal`. Plain `sqlite:///:memory:` gives each
    thread its own separate database, so we swap in a StaticPool engine
    (one shared connection) for the duration of each test.
    """
    engine = build_sqlite_engine(monkeypatch)
    yield
    engine.dispose()


@pytest.fixture
def app():
    application = FastAPI()
    application.include_router(sync_router.router)
    return application


@pytest.fixture
def client(app):
    return ASGITestClient(app)


def _fake_run_sync(db: Session, *, run_id: int) -> SyncRun:
    """Fast stand-in for the real sync -- avoids mocking a JiraClient here."""
    run = db.get(SyncRun, run_id)
    assert run is not None
    run.finished_at = datetime.now(timezone.utc)
    run.status = "success"
    run.worklogs_upserted = 3
    run.worklogs_deleted = 1
    db.commit()
    db.refresh(run)
    return run


def test_status_with_no_runs_returns_null(client):
    response = client.get("/api/sync/status")

    assert response.status_code == 200
    body = response.json()
    assert body["latest_run"] is None
    assert body["is_running"] is False


def test_status_reflects_most_recent_run(client):
    db = db_module.SessionLocal()
    try:
        older = SyncRun(
            started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            finished_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            status="success",
            worklogs_upserted=1,
            worklogs_deleted=0,
        )
        db.add(older)
        db.commit()

        newest = SyncRun(
            started_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            finished_at=None,
            status="running",
            worklogs_upserted=0,
            worklogs_deleted=0,
        )
        db.add(newest)
        db.commit()
        newest_id = newest.id
    finally:
        db.close()

    response = client.get("/api/sync/status")

    assert response.status_code == 200
    body = response.json()
    assert body["latest_run"]["id"] == newest_id
    assert body["is_running"] is True


def test_get_schedule_creates_default_on_fresh_db(client):
    response = client.get("/api/sync/schedule")

    assert response.status_code == 200
    body = response.json()
    assert body["cron_expression"] == "0 * * * *"
    assert body["project_keys"] == ["IN"]
    assert body["jql_filter"] is None


def test_put_schedule_with_valid_cron_persists(client):
    response = client.put("/api/sync/schedule", json={"cron_expression": "*/5 * * * *"})

    assert response.status_code == 200
    body = response.json()
    assert body["cron_expression"] == "*/5 * * * *"
    assert body["project_keys"] == ["IN"]

    follow_up = client.get("/api/sync/schedule")
    assert follow_up.json()["cron_expression"] == "*/5 * * * *"


def test_put_schedule_updates_project_keys_when_provided(client):
    response = client.put(
        "/api/sync/schedule",
        json={"cron_expression": "0 * * * *", "project_keys": ["IN", "OUT"]},
    )

    assert response.status_code == 200
    assert response.json()["project_keys"] == ["IN", "OUT"]


def test_put_schedule_with_jql_filter_persists(client, monkeypatch):
    monkeypatch.setattr(JiraClient, "validate_jql", lambda self, jql: None)

    response = client.put(
        "/api/sync/schedule",
        json={"cron_expression": "0 * * * *", "jql_filter": "labels = keep"},
    )

    assert response.status_code == 200
    assert response.json()["jql_filter"] == "labels = keep"

    follow_up = client.get("/api/sync/schedule")
    assert follow_up.json()["jql_filter"] == "labels = keep"


def test_put_schedule_with_invalid_jql_returns_400(client, monkeypatch):
    def _raise(self, jql):
        raise ValueError("The JQL is invalid")

    monkeypatch.setattr(JiraClient, "validate_jql", _raise)

    response = client.put(
        "/api/sync/schedule",
        json={"cron_expression": "0 * * * *", "jql_filter": "not valid jql"},
    )

    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()


def test_put_schedule_with_invalid_cron_returns_400(client):
    response = client.put("/api/sync/schedule", json={"cron_expression": "not a cron"})

    assert response.status_code == 400


def test_put_schedule_reschedules_running_scheduler(client):
    scheduler_module.start_scheduler()
    scheduler = scheduler_module.get_scheduler()

    response = client.put("/api/sync/schedule", json={"cron_expression": "*/15 * * * *"})

    assert response.status_code == 200
    job = scheduler.get_job(scheduler_module.JOB_ID)
    expected_trigger = CronTrigger.from_crontab("*/15 * * * *")
    assert str(job.trigger) == str(expected_trigger)


def test_trigger_worklogs_returns_run_id_visible_in_status(client, monkeypatch):
    monkeypatch.setattr(sync_router, "run_sync", _fake_run_sync)

    response = client.post("/api/sync/worklogs")

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] > 0
    assert body["status"] == "running"

    status_response = client.get("/api/sync/status")
    assert status_response.json()["latest_run"]["id"] == body["run_id"]


def test_cancel_returns_409_when_nothing_running(client):
    response = client.post("/api/sync/worklogs/cancel")

    assert response.status_code == 409


def test_cancel_sets_flag_on_running_run(client):
    db = db_module.SessionLocal()
    try:
        run = SyncRun(
            started_at=datetime.now(timezone.utc),
            finished_at=None,
            status="running",
            worklogs_upserted=0,
            worklogs_deleted=0,
        )
        db.add(run)
        db.commit()
        run_id = run.id
    finally:
        db.close()

    response = client.post("/api/sync/worklogs/cancel")

    assert response.status_code == 200
    assert response.json() == {"run_id": run_id, "status": "running"}

    db = db_module.SessionLocal()
    try:
        assert db.get(SyncRun, run_id).cancel_requested is True
    finally:
        db.close()


def test_run_sync_job_skips_when_a_run_is_already_in_progress(monkeypatch):
    db = db_module.SessionLocal()
    try:
        db.add(
            SyncRun(
                started_at=datetime.now(timezone.utc),
                finished_at=None,
                status="running",
                worklogs_upserted=0,
                worklogs_deleted=0,
            )
        )
        db.commit()
    finally:
        db.close()

    called = False

    def _fail_if_called(db, *, run_id):
        nonlocal called
        called = True

    monkeypatch.setattr(scheduler_module, "run_sync", _fail_if_called)

    scheduler_module._run_sync_job()

    assert called is False


def test_croniter_validation_rejects_garbage_accepts_valid():
    with pytest.raises(ValueError):
        scheduler_module.validate_cron("not a cron")

    scheduler_module.validate_cron("0 * * * *")  # should not raise
