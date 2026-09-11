"""Cron scheduling for the background sync job.

Wraps an APScheduler BackgroundScheduler around `run_sync`. The scheduler
itself only owns session lifecycle for the scheduled job -- `run_sync` does
all the actual sync work and transaction management.
"""

from __future__ import annotations

from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.core import db as db_module
from app.core.config import settings
from app.models import SyncSchedule
from app.services.sync_service import run_sync

JOB_ID = "sync_job"

_scheduler: BackgroundScheduler | None = None


def validate_cron(cron_expression: str) -> None:
    """Raise ValueError if `cron_expression` is not a valid cron string.

    Validates with the exact parser the scheduler consumes it with
    (APScheduler's CronTrigger), not a different library (e.g. croniter) --
    a syntax accepted by one but rejected by the other would persist an
    unusable schedule that crashes every future scheduler start/reschedule.
    """
    try:
        CronTrigger.from_crontab(cron_expression)
    except ValueError as exc:
        raise ValueError(f"Invalid cron expression {cron_expression!r}: {exc}") from exc


def get_or_create_schedule(db: Session) -> SyncSchedule:
    schedule = db.get(SyncSchedule, 1)
    if schedule is None:
        schedule = SyncSchedule(
            id=1,
            cron_expression=settings.sync_default_cron,
            project_keys=",".join(settings.jira_project_keys),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
    return schedule


def _run_sync_job() -> None:
    db = db_module.SessionLocal()
    try:
        run_sync(db)
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler

    db = db_module.SessionLocal()
    try:
        schedule = get_or_create_schedule(db)
        cron_expression = schedule.cron_expression
    finally:
        db.close()

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _run_sync_job,
        trigger=CronTrigger.from_crontab(cron_expression),
        id=JOB_ID,
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def reschedule(scheduler: BackgroundScheduler, cron_expression: str) -> None:
    if scheduler.get_job(JOB_ID) is not None:
        scheduler.remove_job(JOB_ID)
    scheduler.add_job(
        _run_sync_job,
        trigger=CronTrigger.from_crontab(cron_expression),
        id=JOB_ID,
        replace_existing=True,
    )


def get_scheduler() -> BackgroundScheduler | None:
    return _scheduler
