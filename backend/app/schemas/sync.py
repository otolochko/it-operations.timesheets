from datetime import datetime

from pydantic import BaseModel


class SyncRunSummary(BaseModel):
    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    worklogs_upserted: int
    worklogs_deleted: int
    error: str | None

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
    updated_at: datetime


class SyncScheduleUpdateRequest(BaseModel):
    cron_expression: str
    project_keys: list[str] | None = None
