"""Add ShiftPlanSnapshot table and ShiftPlan.updated_at column.

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
Create Date: 2026-04-25 06:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "s9t0u1v2w3x4"
down_revision: str | Sequence[str] | None = "r8s9t0u1v2w3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: shift_plans に updated_at を追加し、shift_plan_snapshots テーブルを新設する."""
    # shift_plans テーブルに updated_at カラムを追加
    op.add_column(
        "shift_plans",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
        ),
    )

    # shift_plan_snapshots テーブルを新設
    op.create_table(
        "shift_plan_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("shift_plan_id", UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_data", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["shift_plan_id"],
            ["shift_plans.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_shift_plan_snapshots_plan_id",
        "shift_plan_snapshots",
        ["shift_plan_id"],
    )
    op.create_index(
        "ix_shift_plan_snapshots_tenant_id",
        "shift_plan_snapshots",
        ["tenant_id"],
    )


def downgrade() -> None:
    """Downgrade schema: shift_plan_snapshots テーブルを削除し、shift_plans から updated_at を削除する."""
    op.drop_index("ix_shift_plan_snapshots_tenant_id", table_name="shift_plan_snapshots")
    op.drop_index("ix_shift_plan_snapshots_plan_id", table_name="shift_plan_snapshots")
    op.drop_table("shift_plan_snapshots")
    op.drop_column("shift_plans", "updated_at")
