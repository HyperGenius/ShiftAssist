"""Add employment_type_rules table.

Revision ID: p6q7r8s9t0u1
Revises: o5p6q7r8s9t0
Create Date: 2026-04-13 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "p6q7r8s9t0u1"
down_revision: str | Sequence[str] | None = "o5p6q7r8s9t0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: employment_type_rules テーブルを新規作成する."""
    op.create_table(
        "employment_type_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "employment_type_id",
            UUID(as_uuid=True),
            sa.ForeignKey("employment_types.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column(
            "require_default_pair",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("allowed_slot_types", sa.JSON(), nullable=True),
        sa.Column("annual_limit_overrides", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "employment_type_id",
            name="uq_employment_type_rule_employment_type_id",
        ),
    )
    op.create_index(
        "ix_employment_type_rules_tenant_id",
        "employment_type_rules",
        ["tenant_id"],
    )


def downgrade() -> None:
    """Downgrade schema: employment_type_rules テーブルを削除する."""
    op.drop_index(
        "ix_employment_type_rules_tenant_id",
        table_name="employment_type_rules",
    )
    op.drop_table("employment_type_rules")
