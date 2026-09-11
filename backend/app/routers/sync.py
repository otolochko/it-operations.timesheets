"""Sync control API: trigger/inspect sync runs and manage the cron schedule."""

from __future__ import annotations

import threading
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import db as db_module
from app.core.db import get_db
from app.models import SyncRun, SyncSchedule
from app.schemas.sync import (
    SyncRunSummary,
    SyncScheduleResponse,
    SyncScheduleUpdateRequest,
    SyncStatusResponse,
    SyncTriggerResponse,
)
from app.services.scheduler import get_or_create_schedule, get_scheduler, reschedule, validate_cron
from app.services.sync_service import run_sync

router = APIRouter(prefix="/api/sync", tags=["sync"])


def _latest_run(db: Session) -> SyncRun | None:
    return db.scalars(select(SyncRun).order_by(SyncRun.id.desc())).first()


def _run_sync_in_background() -> None:
    db = db_module.SessionLocal()
    try:
        run_sync(db)
    finally:
        db.close()


@router.post("/worklogs", response_model=SyncTriggerResponse)
def trigger_sync(db: Session = Depends(get_db)) -> SyncTriggerResponse:
    """Trigger a sync run without blocking on its full duration.

    `run_sync` commits its "running" SyncRun row synchronously before doing
    any Jira network calls. We run it on a background thread (rather than
    FastAPI's BackgroundTasks, whose callback only executes *after* the
    response is sent -- too late to read back a run id) and poll briefly for
    that row to appear, since the row is committed almost immediately.

    Refuses to start a second run while one is already in progress: run_sync
    reads/advances the single-row `sync_state` watermark, so two concurrent
    runs would race on that row and could corrupt the watermark or double up
    on Jira calls.
    """
    running = _latest_run(db)
    if running is not None and running.status == "running":
        return SyncTriggerResponse(run_id=running.id, status=running.status)

    before_id = db.scalars(select(SyncRun.id).order_by(SyncRun.id.desc())).first() or 0

    thread = threading.Thread(target=_run_sync_in_background, daemon=True)
    thread.start()

    run_id: int | None = None
    for _ in range(200):  # up to ~2s at 10ms intervals
        db.expire_all()
        latest = _latest_run(db)
        if latest is not None and latest.id > before_id:
            run_id = latest.id
            status = latest.status
            break
        time.sleep(0.01)

    if run_id is None:
        raise HTTPException(status_code=500, detail="Sync run did not start in time")

    return SyncTriggerResponse(run_id=run_id, status=status)


@router.get("/status", response_model=SyncStatusResponse)
def get_status(db: Session = Depends(get_db)) -> SyncStatusResponse:
    latest = _latest_run(db)
    if latest is None:
        return SyncStatusResponse(latest_run=None, is_running=False)
    summary = SyncRunSummary.model_validate(latest)
    return SyncStatusResponse(latest_run=summary, is_running=latest.status == "running")


@router.get("/schedule", response_model=SyncScheduleResponse)
def get_schedule(db: Session = Depends(get_db)) -> SyncScheduleResponse:
    schedule = get_or_create_schedule(db)
    return SyncScheduleResponse(
        cron_expression=schedule.cron_expression,
        project_keys=[key for key in schedule.project_keys.split(",") if key],
        updated_at=schedule.updated_at,
    )


@router.put("/schedule", response_model=SyncScheduleResponse)
def update_schedule(
    body: SyncScheduleUpdateRequest, db: Session = Depends(get_db)
) -> SyncScheduleResponse:
    from datetime import datetime, timezone

    try:
        validate_cron(body.cron_expression)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    schedule = get_or_create_schedule(db)
    schedule.cron_expression = body.cron_expression
    if body.project_keys is not None:
        schedule.project_keys = ",".join(body.project_keys)
    schedule.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(schedule)

    scheduler = get_scheduler()
    if scheduler is not None:
        reschedule(scheduler, schedule.cron_expression)

    return SyncScheduleResponse(
        cron_expression=schedule.cron_expression,
        project_keys=[key for key in schedule.project_keys.split(",") if key],
        updated_at=schedule.updated_at,
    )
