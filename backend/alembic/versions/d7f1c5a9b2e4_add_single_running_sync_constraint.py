"""enforce a single running sync run

Revision ID: d7f1c5a9b2e4
Revises: a4b8114a40e5
Create Date: 2026-09-14 15:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7f1c5a9b2e4"
down_revision: Union[str, None] = "a4b8114a40e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Earlier versions relied on an application-level check and may have
    # admitted duplicate running rows.  Preserve the newest run as the only
    # candidate that could still be active; mark older duplicate history as
    # terminal before enforcing the invariant.  Production upgrades should
    # still be performed while sync workers are stopped.
    op.execute(
        """
        UPDATE sync_runs
        SET status = 'failed',
            finished_at = COALESCE(finished_at, CURRENT_TIMESTAMP),
            error = COALESCE(error, 'Superseded by single-flight sync migration')
        WHERE status = 'running'
          AND id <> (SELECT MAX(id) FROM sync_runs WHERE status = 'running')
        """
    )
    op.create_index(
        "uq_sync_runs_single_running",
        "sync_runs",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'running'"),
        sqlite_where=sa.text("status = 'running'"),
    )


def downgrade() -> None:
    op.drop_index("uq_sync_runs_single_running", table_name="sync_runs")
