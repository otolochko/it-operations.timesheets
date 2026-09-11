"""Read-only timesheets API endpoints."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.timesheets import IssueDrilldownResponse, TimesheetGridResponse
from app.services.timesheet_service import get_issue_drilldown, get_timesheet_grid

router = APIRouter(prefix="/api/timesheets", tags=["timesheets"])


@router.get("", response_model=TimesheetGridResponse)
def read_timesheet_grid(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    group: Literal["day", "week"] = Query("day"),
    db: Session = Depends(get_db),
) -> TimesheetGridResponse:
    return get_timesheet_grid(db, from_date, to_date, group)


@router.get("/issues", response_model=IssueDrilldownResponse)
def read_issue_drilldown(
    author: str = Query(..., alias="author"),
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    db: Session = Depends(get_db),
) -> IssueDrilldownResponse:
    return get_issue_drilldown(db, author, from_date, to_date)
