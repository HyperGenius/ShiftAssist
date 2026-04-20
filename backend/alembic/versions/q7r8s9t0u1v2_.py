"""Add custom_rules table and workers.custom_rule_id.

Revision ID: q7r8s9t0u1v2
Revises: p6q7r8s9t0u1
Create Date: 2026-04-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "q7r8s9t0u1v2"
down_revision: str | Sequence[str] | None = "p6q7r8s9t0u1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: custom_rules テーブルを新規作成し、workers.custom_rule_id カラムを追加する."""
    # 1. custom_rules テーブルを作成
    op.create_table(
        "custom_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("allowed_slot_types", sa.JSON(), nullable=True),
        sa.Column("annual_limit_overrides", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("tenant_id", "name", name="uq_custom_rule_tenant_name"),
    )
    op.create_index(
        "ix_custom_rules_tenant_id",
        "custom_rules",
        ["tenant_id"],
    )

    # 2. workers テーブルに custom_rule_id カラムを追加
    op.add_column(
        "workers",
        sa.Column(
            "custom_rule_id",
            UUID(as_uuid=True),
            sa.ForeignKey("custom_rules.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema: workers.custom_rule_id カラムを削除し、custom_rules テーブルを削除する."""
    op.drop_column("workers", "custom_rule_id")
    op.drop_index("ix_custom_rules_tenant_id", table_name="custom_rules")
    op.drop_table("custom_rules")
