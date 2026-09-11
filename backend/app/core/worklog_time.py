"""Calendar-date handling for Jira worklogs.

The original numeric offset is authoritative for deciding which local calendar
day contains a worklog.
"""

from datetime import date, datetime, timedelta, timezone


def _work_date_at_offset(started: datetime, offset_seconds: int) -> date:
    """Return the calendar date at ``offset_seconds`` for an aware datetime."""
    if started.tzinfo is None or started.utcoffset() is None:
        raise ValueError("started must be timezone-aware")

    original_offset = timezone(timedelta(seconds=offset_seconds))
    return started.astimezone(original_offset).date()


def work_date_from_jira_json(worklog_json: dict) -> date:
    """Extract the author's local work date from a Jira worklog payload."""
    started = datetime.fromisoformat(worklog_json["started"])
    offset = started.utcoffset()
    if offset is None:
        raise ValueError("Jira worklog 'started' must include a numeric offset")

    return _work_date_at_offset(started, int(offset.total_seconds()))


def work_date_from_row(started: datetime, started_utc_offset: int) -> date:
    """Recover the original local work date from a stored worklog row."""
    return _work_date_at_offset(started, started_utc_offset)
