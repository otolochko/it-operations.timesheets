"""Read-only timesheets API endpoints."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.timesheets import IssueDrilldownResponse, TimesheetGridResponse
from app.services.export_service import build_csv, build_xlsx
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


@router.get("/export")
def export_timesheets(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    group: Literal["day", "week"] = Query("day"),
    export_format: Literal["csv", "xlsx"] = Query("csv", alias="format"),
    dataset: Literal["matrix", "raw", "issues"] = Query("matrix"),
    db: Session = Depends(get_db),
) -> Response:
    if export_format == "xlsx":
        content = build_xlsx(db, from_date, to_date, group)
        filename = f"timesheets-{from_date}-to-{to_date}.xlsx"
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    content = build_csv(db, dataset, from_date, to_date, group)
    filename = f"timesheets-{from_date}-to-{to_date}-{dataset}.csv"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
