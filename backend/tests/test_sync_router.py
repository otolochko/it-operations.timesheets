"""Tests for the sync control API and scheduler wiring."""

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core import db as db_module
from app.core.db import Base
from app.models import SyncRun
from app.routers import sync as sync_router
from app.services import scheduler as scheduler_module
from apscheduler.triggers.cron import CronTrigger


@pytest.fixture(autouse=True)
def shared_sqlite_engine(monkeypatch):
    """Point app.core.db at a single shared-connection sqlite engine.

    The router and scheduler open their own sessions on background threads
    via `db_module.SessionLocal`. Plain `sqlite:///:memory:` gives each
    thread its own separate database, so we swap in a StaticPool engine
    (one shared connection) for the duration of each test.
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = __import__("sqlalchemy.orm", fromlist=["sessionmaker"]).sessionmaker(
        bind=engine, autoflush=False, autocommit=False
    )
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", SessionLocal)
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def reset_global_scheduler():
    yield
    scheduler = scheduler_module.get_scheduler()
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler_module._scheduler = None


@pytest.fixture
def app():
    application = FastAPI()
    application.include_router(sync_router.router)
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


def _fake_run_sync(db: Session) -> SyncRun:
    """Fast stand-in for the real sync -- avoids mocking a JiraClient here."""
    now = datetime.now(timezone.utc)
    run = SyncRun(
        started_at=now,
        finished_at=now,
        status="success",
        worklogs_upserted=3,
        worklogs_deleted=1,
    )
    db.add(run)
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
    assert body["status"] == "success"

    status_response = client.get("/api/sync/status")
    assert status_response.json()["latest_run"]["id"] == body["run_id"]


def test_croniter_validation_rejects_garbage_accepts_valid():
    with pytest.raises(ValueError):
        scheduler_module.validate_cron("not a cron")

    scheduler_module.validate_cron("0 * * * *")  # should not raise
