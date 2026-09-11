from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.issue import Issue


class Worklog(Base):
    __tablename__ = "worklogs"
    __table_args__ = (
        Index("ix_worklogs_work_date", "work_date"),
        Index("ix_worklogs_author_account_id_work_date", "author_account_id", "work_date"),
        Index("ix_worklogs_issue_id", "issue_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    issue_id: Mapped[str] = mapped_column(ForeignKey("issues.id"))
    author_account_id: Mapped[str] = mapped_column(String)
    author_display_name: Mapped[str] = mapped_column(String)
    time_spent_seconds: Mapped[int] = mapped_column(Integer)
    # Original local timestamp as returned by Jira. Do NOT normalize to UTC.
    started: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # UTC offset (seconds) of `started`, stored separately so the correct
    # local calendar date can be recomputed later.
    started_utc_offset: Mapped[int] = mapped_column(Integer)
    work_date: Mapped[date] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    issue: Mapped["Issue"] = relationship(back_populates="worklogs")
