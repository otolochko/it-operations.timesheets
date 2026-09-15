from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SyncRun(Base):
    """Per-run history for the sync status UI (last sync status / log viewer)."""

    __tablename__ = "sync_runs"
    # This is the cross-process single-flight guard.  A partial unique index
    # allows an unlimited history of terminal runs while making two committed
    # ``running`` rows impossible.  It is supported by both production
    # PostgreSQL and SQLite, which keeps the concurrency contract testable.
    __table_args__ = (
        Index(
            "uq_sync_runs_single_running",
            "status",
            unique=True,
            postgresql_where=text("status = 'running'"),
            sqlite_where=text("status = 'running'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String)  # "running" | "success" | "failed" | "cancelled"
    worklogs_upserted: Mapped[int] = mapped_column(Integer, default=0)
    worklogs_deleted: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    log_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    # progress_total is null while the current phase's size is not yet known
    # (e.g. paginating a Jira feed of unknown length) -- the frontend renders
    # an indeterminate progress bar in that case.
    progress_phase: Mapped[str | None] = mapped_column(String, nullable=True)
    progress_current: Mapped[int] = mapped_column(Integer, default=0)
    progress_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
