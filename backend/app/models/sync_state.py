from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SyncState(Base):
    """Single-row watermark table. Row id is always 1."""

    __tablename__ = "sync_state"
    __table_args__ = (CheckConstraint("id = 1", name="ck_sync_state_single_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_watermark: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
