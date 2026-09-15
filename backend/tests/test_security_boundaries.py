"""Request validation that bounds unauthenticated internal API resource use."""

from datetime import date

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.routers.timesheets import MAX_REPORT_RANGE_DAYS, _validate_report_range
from app.schemas.sync import SyncScheduleUpdateRequest


def test_report_range_accepts_configured_limit() -> None:
    _validate_report_range(date(2026, 1, 1), date(2026, 1, 1))
    _validate_report_range(
        date(2026, 1, 1), date(2026, 1, 1).fromordinal(date(2026, 1, 1).toordinal() + 365)
    )


def test_report_range_rejects_more_than_configured_limit() -> None:
    with pytest.raises(HTTPException, match=str(MAX_REPORT_RANGE_DAYS)):
        _validate_report_range(date(2026, 1, 1), date(2027, 1, 2))


def test_schedule_payload_rejects_oversized_or_ambiguous_values() -> None:
    with pytest.raises(ValidationError):
        SyncScheduleUpdateRequest(cron_expression="x" * 129)
    with pytest.raises(ValidationError):
        SyncScheduleUpdateRequest(cron_expression="0 * * * *", project_keys=["IN", "IN"])
    with pytest.raises(ValidationError):
        SyncScheduleUpdateRequest(cron_expression="0 * * * *", project_keys=["IN,OUT"])
