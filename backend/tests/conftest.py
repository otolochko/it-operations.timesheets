"""Test-only configuration supplied before application modules are imported."""

import os


os.environ.update(
    {
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
        "JIRA_BASE_URL": "https://jira.example.test",
        "JIRA_EMAIL": "technical-user@example.test",
        "JIRA_API_TOKEN": "test-token",
        "JIRA_MAX_RETRIES": "2",
        "JIRA_RETRY_BASE_SECONDS": "0.01",
        "JIRA_PROJECT_KEYS": "IN",
        "SYNC_DEFAULT_CRON": "0 * * * *",
    }
)

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core import db as db_module  # noqa: E402
from app.core.db import Base  # noqa: E402


def build_sqlite_engine(monkeypatch, *, on_create=None):
    """Build a StaticPool in-memory SQLite engine and monkeypatch it in as
    app.core.db's engine/SessionLocal.

    Request-scoped `get_db()` and background-thread code (the scheduler,
    the sync trigger's background thread) both read `db_module.SessionLocal`
    at call time, so patching it here is the one seam that makes both paths
    see the same test database. A plain `sqlite:///:memory:` engine gives
    every new connection its own separate database, hence StaticPool (a
    single shared connection) instead.

    `on_create`, if given, runs against the engine before the schema is
    created (e.g. to register a SQLite connection function), so it applies
    before the first connection is opened.
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    if on_create is not None:
        on_create(engine)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(
        db_module, "SessionLocal", sessionmaker(bind=engine, autoflush=False, autocommit=False)
    )
    return engine


@pytest.fixture(autouse=True)
def _reset_global_scheduler():
    """Stop and clear the module-global BackgroundScheduler singleton.

    Any test that goes through the app's startup hook or the sync router
    may start a real APScheduler instance; leaving it running would leak
    into whichever test runs next.
    """
    yield
    from app.services import scheduler as scheduler_module

    scheduler = scheduler_module.get_scheduler()
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler_module._scheduler = None
