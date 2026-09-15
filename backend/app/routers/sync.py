"""Sync control API: trigger/inspect sync runs and manage the cron schedule."""

from __future__ import annotations

import threading
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import db as db_module
from app.core.db import get_db
from app.core.jira_http import JiraClient
from app.models import SyncRun, SyncSchedule
from app.schemas.sync import (
    SyncRunSummary,
    SyncScheduleResponse,
    SyncScheduleUpdateRequest,
    SyncStatusResponse,
    SyncTriggerResponse,
)
from app.services.scheduler import get_scheduler, reschedule, validate_cron
from app.services.sync_service import get_or_create_schedule, reserve_sync_run, run_sync

router = APIRouter(prefix="/api/sync", tags=["sync"])


def _latest_run(db: Session) -> SyncRun | None:
    return db.scalars(select(SyncRun).order_by(SyncRun.id.desc())).first()


def _schedule_response(schedule: SyncSchedule) -> SyncScheduleResponse:
    return SyncScheduleResponse(
        cron_expression=schedule.cron_expression,
        project_keys=[key for key in schedule.project_keys.split(",") if key],
        jql_filter=schedule.jql_filter,
        updated_at=schedule.updated_at,
    )


def _run_sync_in_background(run_id: int) -> None:
    db = db_module.SessionLocal()
    try:
        run_sync(db, run_id=run_id)
    finally:
        db.close()


@router.post("/worklogs", response_model=SyncTriggerResponse)
def trigger_sync(db: Session = Depends(get_db)) -> SyncTriggerResponse:
    """Trigger a sync run without blocking on its full duration.

    The running row is reserved synchronously by a database-enforced unique
    constraint, before the worker is started.  This closes the race between
    simultaneous HTTP requests and scheduled jobs.
    """
    run, reserved = reserve_sync_run(db)
    if not reserved:
        return SyncTriggerResponse(run_id=run.id, status=run.status)

    thread = threading.Thread(target=_run_sync_in_background, args=(run.id,), daemon=True)
    thread.start()
    return SyncTriggerResponse(run_id=run.id, status=run.status)


@router.post("/worklogs/cancel", response_model=SyncTriggerResponse)
def cancel_sync(db: Session = Depends(get_db)) -> SyncTriggerResponse:
    """Request cancellation of the in-progress sync run, if any.

    Cooperative: `run_sync` only notices the flag at its own checkpoints
    (between Jira calls), so the run stops shortly after this returns, not
    immediately.
    """
    # Lock the row while checking its state.  This cannot race a worker's
    # final locked cancellation check/success transition.
    running = db.scalars(
        select(SyncRun)
        .where(SyncRun.status == "running")
        .with_for_update()
    ).first()
    if running is None:
        raise HTTPException(status_code=409, detail="No sync run is currently in progress")

    running.cancel_requested = True
    db.commit()
    return SyncTriggerResponse(run_id=running.id, status=running.status)


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
    return _schedule_response(schedule)


@router.put("/schedule", response_model=SyncScheduleResponse)
def update_schedule(
    body: SyncScheduleUpdateRequest, db: Session = Depends(get_db)
) -> SyncScheduleResponse:
    try:
        validate_cron(body.cron_expression)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if body.jql_filter is not None:
        jql_filter = body.jql_filter.strip()
        if jql_filter:
            try:
                with JiraClient() as client:
                    client.validate_jql(jql_filter)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

    schedule = get_or_create_schedule(db)
    schedule.cron_expression = body.cron_expression
    if body.project_keys is not None:
        schedule.project_keys = ",".join(body.project_keys)
    if body.jql_filter is not None:
        schedule.jql_filter = body.jql_filter.strip() or None
    schedule.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(schedule)

    scheduler = get_scheduler()
    if scheduler is not None:
        reschedule(scheduler, schedule.cron_expression)

    return _schedule_response(schedule)
