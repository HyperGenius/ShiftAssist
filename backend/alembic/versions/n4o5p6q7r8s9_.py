"""Add worker_monthly_slot_stats table.

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2026-04-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "n4o5p6q7r8s9"
down_revision: str | Sequence[str] | None = "m3n4o5p6q7r8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: worker_monthly_slot_stats テーブルを追加する."""
    op.create_table(
        "worker_monthly_slot_stats",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column(
            "worker_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("year_month", sa.String(), nullable=False),
        sa.Column(
            "slot_type",
            sa.Enum(
                "weekday_night",
                "sat_day",
                "sat_night",
                "sun_hol_day",
                "sun_hol_night",
                "long_hol_day",
                "long_hol_night",
                "sat_pre_hol_night",
                name="slottypeenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("weekday", sa.Integer(), nullable=True),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_worker_monthly_slot_stats",
        "worker_monthly_slot_stats",
        ["tenant_id", "worker_id", "year_month", "slot_type", "weekday"],
    )
    op.create_index(
        "ix_worker_monthly_slot_stats_tenant_ym",
        "worker_monthly_slot_stats",
        ["tenant_id", "year_month"],
    )
    op.create_index(
        "ix_worker_monthly_slot_stats_tenant_id",
        "worker_monthly_slot_stats",
        ["tenant_id"],
    )


def downgrade() -> None:
    """Downgrade schema: worker_monthly_slot_stats テーブルを削除する."""
    op.drop_index(
        "ix_worker_monthly_slot_stats_tenant_id",
        table_name="worker_monthly_slot_stats",
    )
    op.drop_index(
        "ix_worker_monthly_slot_stats_tenant_ym",
        table_name="worker_monthly_slot_stats",
    )
    op.drop_constraint(
        "uq_worker_monthly_slot_stats",
        "worker_monthly_slot_stats",
        type_="unique",
    )
    op.drop_table("worker_monthly_slot_stats")
