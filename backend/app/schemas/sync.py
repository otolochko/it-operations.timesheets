from datetime import datetime

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator


ProjectKey = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class SyncRunSummary(BaseModel):
    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    worklogs_upserted: int
    worklogs_deleted: int
    error: str | None
    log_text: str | None
    progress_phase: str | None
    progress_current: int
    progress_total: int | None

    model_config = {"from_attributes": True}


class SyncStatusResponse(BaseModel):
    latest_run: SyncRunSummary | None
    is_running: bool


class SyncTriggerResponse(BaseModel):
    run_id: int
    status: str


class SyncScheduleResponse(BaseModel):
    cron_expression: str
    project_keys: list[str]
    jql_filter: str | None
    updated_at: datetime


class SyncScheduleUpdateRequest(BaseModel):
    cron_expression: str = Field(min_length=1, max_length=128)
    project_keys: list[ProjectKey] | None = Field(default=None, max_length=100)
    jql_filter: str | None = Field(default=None, max_length=10_000)

    @field_validator("project_keys")
    @classmethod
    def validate_project_keys(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if len(set(value)) != len(value):
            raise ValueError("project_keys must not contain duplicates")
        for key in value:
            if "," in key or any(ord(character) < 0x20 for character in key):
                raise ValueError("project_keys contain an invalid character")
        return value
