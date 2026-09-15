"""Cron scheduling for the background sync job.

Wraps an APScheduler BackgroundScheduler around `run_sync`. The scheduler
itself only owns session lifecycle for the scheduled job -- `run_sync` does
all the actual sync work and transaction management.
"""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core import db as db_module
from app.services.sync_service import get_or_create_schedule, reserve_sync_run, run_sync

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


def _run_sync_job() -> None:
    """Cron-triggered sync. Skips if a run (manual or a prior cron fire) is
    already in progress.  Reservation is database-enforced, so it is safe
    against races with HTTP handlers and other scheduler workers.
    """
    db = db_module.SessionLocal()
    try:
        run, reserved = reserve_sync_run(db)
        if not reserved:
            return
        run_sync(db, run_id=run.id)
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
