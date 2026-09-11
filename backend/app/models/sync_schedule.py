from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SyncSchedule(Base):
    """Single-row cron + scope config. Row id is always 1."""

    __tablename__ = "sync_schedule"
    __table_args__ = (CheckConstraint("id = 1", name="ck_sync_schedule_single_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cron_expression: Mapped[str] = mapped_column(String)
    project_keys: Mapped[str] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
