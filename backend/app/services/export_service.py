"""CSV/Excel export builders for the timesheets grid, raw cells, and issue totals.

Reuses `get_timesheet_grid` / `get_all_issue_totals` for aggregation; this
module only shapes those results into file formats. Must never call Jira.
"""

from __future__ import annotations

import csv
import io
from datetime import date
from typing import Literal

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app.schemas.timesheets import TimesheetGridResponse
from app.services.timesheet_service import get_all_issue_totals, get_timesheet_grid

Dataset = Literal["matrix", "raw", "issues"]

# Leading characters a spreadsheet treats as the start of a formula.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe_cell(value):
    """Neutralize spreadsheet formula injection in a cell value.

    Issue summaries, display names and project/issue keys all come from Jira,
    where any user can set them. A summary like `=WEBSERVICE("http://...")`
    would execute when the exported file is opened in Excel/LibreOffice, so
    string values starting with a formula character get an apostrophe prefix
    (the spreadsheet reads it as a text marker and doesn't display it).
    Numbers pass through untouched so Excel can still sum them.
    """
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def _safe_row(row: list) -> list:
    return [_safe_cell(value) for value in row]


def _sorted_periods(grid: TimesheetGridResponse) -> list[date]:
    return sorted({cell.period_start for cell in grid.cells})


def _sorted_authors(grid: TimesheetGridResponse) -> list[tuple[str, str]]:
    """Return (account_id, display_name) pairs, sorted by display name."""
    authors: dict[str, str] = {}
    for cell in grid.cells:
        authors[cell.author_account_id] = cell.author_display_name
    return sorted(authors.items(), key=lambda pair: pair[1])


def _matrix_rows(grid: TimesheetGridResponse) -> tuple[list[str], list[list], list]:
    """Build the matrix header, body rows, and totals row for the given grid.

    Returns (header, rows, totals_row). `rows` and `totals_row` contain
    hours as floats (1 decimal), ready to write to CSV or XLSX.
    """
    periods = _sorted_periods(grid)
    authors = _sorted_authors(grid)

    hours_by_author_period: dict[tuple[str, date], float] = {}
    for cell in grid.cells:
        hours_by_author_period[(cell.author_account_id, cell.period_start)] = (
            cell.total_seconds / 3600.0
        )

    header = ["Author"] + [p.isoformat() for p in periods] + ["Total"]

    rows: list[list] = []
    period_totals = [0.0 for _ in periods]
    for account_id, display_name in authors:
        row: list = [display_name]
        author_total = 0.0
        for idx, period in enumerate(periods):
            hours = round(hours_by_author_period.get((account_id, period), 0.0), 1)
            row.append(hours)
            author_total += hours
            period_totals[idx] += hours
        row.append(round(author_total, 1))
        rows.append(row)

    totals_row = ["Total"] + [round(t, 1) for t in period_totals] + [
        round(sum(period_totals), 1)
    ]

    return header, rows, totals_row


def _raw_rows(grid: TimesheetGridResponse) -> tuple[list[str], list[list]]:
    header = ["Author", "Account ID", "Period", "Hours"]
    rows = [
        [
            cell.author_display_name,
            cell.author_account_id,
            cell.period_start.isoformat(),
            round(cell.total_seconds / 3600.0, 1),
        ]
        for cell in sorted(grid.cells, key=lambda c: (c.author_display_name, c.period_start))
    ]
    return header, rows


def _issues_rows(db: Session, from_date: date, to_date: date) -> tuple[list[str], list[list]]:
    header = ["Author", "Account ID", "Issue Key", "Issue Summary", "Project Key", "Hours", "Worklogs"]
    totals = get_all_issue_totals(db, from_date, to_date)
    rows = [
        [
            entry["author_display_name"],
            entry["author_account_id"],
            entry["issue_key"],
            entry["issue_summary"],
            entry["project_key"],
            round(entry["total_seconds"] / 3600.0, 1),
            entry["worklog_count"],
        ]
        for entry in totals
    ]
    return header, rows


def _dataset_rows(
    db: Session,
    dataset: Dataset,
    grid: TimesheetGridResponse,
    from_date: date,
    to_date: date,
) -> tuple[list[str], list[list]]:
    if dataset == "matrix":
        header, rows, totals_row = _matrix_rows(grid)
        return header, [*rows, totals_row]
    if dataset == "raw":
        return _raw_rows(grid)
    return _issues_rows(db, from_date, to_date)


def build_csv(
    db: Session,
    dataset: Dataset,
    from_date: date,
    to_date: date,
    group: Literal["day", "week"],
) -> str:
    grid = get_timesheet_grid(db, from_date, to_date, group)
    header, rows = _dataset_rows(db, dataset, grid, from_date, to_date)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_safe_row(header))
    writer.writerows(_safe_row(row) for row in rows)
    return buffer.getvalue()


def _write_sheet(ws, header: list[str], rows: list[list]) -> None:
    ws.append(_safe_row(header))
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"

    for row in rows:
        ws.append(_safe_row(row))

    for idx, title in enumerate(header, start=1):
        max_len = len(str(title))
        for row in rows:
            value = row[idx - 1] if idx - 1 < len(row) else ""
            max_len = max(max_len, len(str(value)))
        ws.column_dimensions[get_column_letter(idx)].width = min(max(max_len + 2, 10), 40)


def build_xlsx(
    db: Session,
    from_date: date,
    to_date: date,
    group: Literal["day", "week"],
) -> bytes:
    grid = get_timesheet_grid(db, from_date, to_date, group)

    wb = Workbook()

    matrix_header, matrix_body, matrix_totals = _matrix_rows(grid)
    ws_matrix = wb.active
    ws_matrix.title = "Matrix"
    _write_sheet(ws_matrix, matrix_header, [*matrix_body, matrix_totals])
    for cell in ws_matrix[ws_matrix.max_row]:
        cell.font = Font(bold=True)
    ws_matrix.freeze_panes = "B2"

    summary = grid.summary
    summary_start = ws_matrix.max_row + 2
    summary_rows = [
        ("Total hours", round(summary.total_hours, 1)),
        ("Author count", summary.author_count),
        ("Issue count", summary.issue_count),
        ("Avg hours / author", round(summary.average_hours_per_author, 1)),
    ]
    for offset, (label, value) in enumerate(summary_rows):
        row_idx = summary_start + offset
        # Sanitized like every other written cell, so the rule holds without
        # exceptions even though these labels/values aren't user-controlled.
        ws_matrix.cell(row=row_idx, column=1, value=_safe_cell(label)).font = Font(bold=True)
        ws_matrix.cell(row=row_idx, column=2, value=_safe_cell(value))

    raw_header, raw_rows = _raw_rows(grid)
    ws_raw = wb.create_sheet("Raw")
    _write_sheet(ws_raw, raw_header, raw_rows)

    issues_header, issues_rows = _issues_rows(db, from_date, to_date)
    ws_issues = wb.create_sheet("Issues")
    _write_sheet(ws_issues, issues_header, issues_rows)

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()
