"""Response models for the timesheets read API."""

from datetime import date
from typing import Literal

from pydantic import BaseModel


class TimesheetCell(BaseModel):
    author_account_id: str
    author_display_name: str
    period_start: date
    total_seconds: int


class TimesheetSummary(BaseModel):
    total_hours: float
    author_count: int
    issue_count: int
    average_hours_per_author: float


class TimesheetGridResponse(BaseModel):
    from_date: date
    to_date: date
    group: Literal["day", "week"]
    cells: list[TimesheetCell]
    summary: TimesheetSummary


class IssueWorklogEntry(BaseModel):
    issue_id: str
    issue_key: str
    issue_summary: str
    total_seconds: int
    worklog_count: int


class IssueDrilldownResponse(BaseModel):
    author_account_id: str
    author_display_name: str | None
    from_date: date
    to_date: date
    issues: list[IssueWorklogEntry]
