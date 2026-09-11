from datetime import date, datetime, timedelta, timezone

import pytest

from app.core.worklog_time import work_date_from_jira_json, work_date_from_row


def _offset_text(offset_minutes: int) -> str:
    sign = "+" if offset_minutes >= 0 else "-"
    hours, minutes = divmod(abs(offset_minutes), 60)
    return f"{sign}{hours:02d}{minutes:02d}"


@pytest.mark.parametrize(
    ("started_text", "expected"),
    [
        ("2026-09-11T08:30:00.000+0200", date(2026, 9, 11)),
        ("2026-09-11T08:30:00.000-0500", date(2026, 9, 11)),
        ("2026-09-11T08:30:00.000+0000", date(2026, 9, 11)),
        ("2026-09-11T08:30:00.000+1400", date(2026, 9, 11)),
        ("2026-09-11T08:30:00.000-1200", date(2026, 9, 11)),
    ],
)
def test_basic_offsets(started_text: str, expected: date) -> None:
    local_started = datetime.fromisoformat(started_text)
    offset_seconds = int(local_started.utcoffset().total_seconds())
    stored_started = local_started.astimezone(timezone.utc)

    assert work_date_from_jira_json({"started": started_text}) == expected
    assert work_date_from_row(stored_started, offset_seconds) == expected


@pytest.mark.parametrize(
    ("started_text", "expected", "utc_date"),
    [
        ("2026-09-11T00:15:00.000+1400", date(2026, 9, 11), date(2026, 9, 10)),
        ("2026-09-11T23:45:00.000-1200", date(2026, 9, 11), date(2026, 9, 12)),
        ("2026-09-11T00:15:00.000+0200", date(2026, 9, 11), date(2026, 9, 10)),
        ("2026-09-11T23:45:00.000-0500", date(2026, 9, 11), date(2026, 9, 12)),
    ],
)
def test_local_day_wins_near_midnight(
    started_text: str, expected: date, utc_date: date
) -> None:
    local_started = datetime.fromisoformat(started_text)
    stored_started = local_started.astimezone(timezone.utc)
    offset_seconds = int(local_started.utcoffset().total_seconds())

    assert stored_started.date() == utc_date
    assert work_date_from_jira_json({"started": started_text}) == expected
    assert work_date_from_row(stored_started, offset_seconds) == expected


def test_json_and_stored_row_agree_across_supported_offset_range() -> None:
    expected = date(2026, 9, 11)

    for offset_minutes in range(-12 * 60, 14 * 60 + 1, 30):
        local_time = "00:15:00.000" if offset_minutes >= 0 else "23:45:00.000"
        started_text = (
            f"{expected.isoformat()}T{local_time}{_offset_text(offset_minutes)}"
        )
        local_started = datetime.fromisoformat(started_text)
        stored_started = local_started.astimezone(timezone.utc)
        offset_seconds = int(timedelta(minutes=offset_minutes).total_seconds())

        json_date = work_date_from_jira_json({"started": started_text})
        row_date = work_date_from_row(stored_started, offset_seconds)

        assert json_date == expected
        assert row_date == json_date


@pytest.mark.parametrize("started_text", ["not-a-timestamp", "2026-09-11T08:30:00"])
def test_invalid_jira_started_is_rejected(started_text: str) -> None:
    with pytest.raises(ValueError):
        work_date_from_jira_json({"started": started_text})


def test_naive_stored_datetime_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        work_date_from_row(datetime(2026, 9, 11, 8, 30), 7200)
