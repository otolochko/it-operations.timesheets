"""Read-only aggregation queries backing the timesheets API.

These functions only ever query the already-synced `worklogs`/`issues`
tables in PostgreSQL. They must never call Jira.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Issue, Worklog
from app.schemas.timesheets import (
    IssueDrilldownResponse,
    IssueWorklogEntry,
    TimesheetCell,
    TimesheetGridResponse,
    TimesheetSummary,
)


def get_timesheet_grid(
    db: Session,
    from_date: date,
    to_date: date,
    group: Literal["day", "week"],
) -> TimesheetGridResponse:
    date_filter = Worklog.work_date.between(from_date, to_date)

    if group == "week":
        # Postgres ISO week (Monday-start), returned as a timestamp; the
        # response schema coerces it down to a plain date.
        period_col = func.date_trunc("week", Worklog.work_date)
    else:
        period_col = Worklog.work_date
    period_col = period_col.label("period_start")

    grid_stmt = (
        select(
            Worklog.author_account_id,
            Worklog.author_display_name,
            period_col,
            func.sum(Worklog.time_spent_seconds).label("total_seconds"),
        )
        .where(date_filter)
        .group_by(Worklog.author_account_id, Worklog.author_display_name, period_col)
        .order_by(period_col, Worklog.author_account_id)
    )

    cells = [
        TimesheetCell(
            author_account_id=row.author_account_id,
            author_display_name=row.author_display_name,
            period_start=row.period_start,
            total_seconds=int(row.total_seconds),
        )
        for row in db.execute(grid_stmt)
    ]

    summary_stmt = select(
        func.coalesce(func.sum(Worklog.time_spent_seconds), 0),
        func.count(func.distinct(Worklog.author_account_id)),
        func.count(func.distinct(Worklog.issue_id)),
    ).where(date_filter)

    total_seconds, author_count, issue_count = db.execute(summary_stmt).one()
    total_hours = total_seconds / 3600.0
    average_hours_per_author = total_hours / author_count if author_count > 0 else 0.0

    summary = TimesheetSummary(
        total_hours=total_hours,
        author_count=author_count,
        issue_count=issue_count,
        average_hours_per_author=average_hours_per_author,
    )

    return TimesheetGridResponse(
        from_date=from_date,
        to_date=to_date,
        group=group,
        cells=cells,
        summary=summary,
    )


def get_issue_drilldown(
    db: Session,
    author_account_id: str,
    from_date: date,
    to_date: date,
) -> IssueDrilldownResponse:
    date_filter = Worklog.work_date.between(from_date, to_date)

    display_name = db.execute(
        select(Worklog.author_display_name)
        .where(Worklog.author_account_id == author_account_id, date_filter)
        .limit(1)
    ).scalar_one_or_none()

    issues_stmt = (
        select(
            Issue.id,
            Issue.key,
            Issue.summary,
            func.sum(Worklog.time_spent_seconds).label("total_seconds"),
            func.count(Worklog.id).label("worklog_count"),
        )
        .join(Issue, Issue.id == Worklog.issue_id)
        .where(Worklog.author_account_id == author_account_id, date_filter)
        .group_by(Issue.id, Issue.key, Issue.summary)
        .order_by(Issue.key)
    )

    issues = [
        IssueWorklogEntry(
            issue_id=row.id,
            issue_key=row.key,
            issue_summary=row.summary,
            total_seconds=int(row.total_seconds),
            worklog_count=int(row.worklog_count),
        )
        for row in db.execute(issues_stmt)
    ]

    return IssueDrilldownResponse(
        author_account_id=author_account_id,
        author_display_name=display_name,
        from_date=from_date,
        to_date=to_date,
        issues=issues,
    )
