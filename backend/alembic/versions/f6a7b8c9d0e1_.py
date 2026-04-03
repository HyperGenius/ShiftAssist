"""add worker joined_at, tenant_stats_configs, and performance indexes.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-03 02:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. workers テーブルに joined_at カラムを追加
    op.add_column(
        "workers",
        sa.Column("joined_at", sa.Date(), nullable=True),
    )

    # 2. tenant_stats_configs テーブルを作成
    op.create_table(
        "tenant_stats_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column(
            "stats_period_months", sa.Integer(), nullable=False, server_default="12"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_stats_configs_tenant_id"),
    )
    op.create_index(
        "ix_tenant_stats_configs_tenant_id",
        "tenant_stats_configs",
        ["tenant_id"],
    )

    # 3. shift_plans に複合インデックスを追加（統計クエリのパフォーマンス最適化）
    op.create_index(
        "ix_shift_plans_tenant_status_month",
        "shift_plans",
        ["tenant_id", "status", "target_year_month"],
    )

    # 4. shift_assignments に複合インデックスを追加（統計クエリのパフォーマンス最適化）
    op.create_index(
        "ix_shift_assignments_worker_slot",
        "shift_assignments",
        ["worker_id", "slot_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # 4. shift_assignments の複合インデックスを削除
    op.drop_index(
        "ix_shift_assignments_worker_slot", table_name="shift_assignments"
    )

    # 3. shift_plans の複合インデックスを削除
    op.drop_index(
        "ix_shift_plans_tenant_status_month", table_name="shift_plans"
    )

    # 2. tenant_stats_configs テーブルを削除
    op.drop_index(
        "ix_tenant_stats_configs_tenant_id", table_name="tenant_stats_configs"
    )
    op.drop_table("tenant_stats_configs")

    # 1. workers テーブルから joined_at カラムを削除
    op.drop_column("workers", "joined_at")
