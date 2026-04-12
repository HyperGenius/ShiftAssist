"""Add is_default to employment_types and create partial unique index.

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-04-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "o5p6q7r8s9t0"
down_revision: str | Sequence[str] | None = "n4o5p6q7r8s9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: employment_types に is_default カラムを追加し、Partial Unique Index を作成する."""
    # 1. is_default カラムを追加（デフォルト FALSE）
    op.add_column(
        "employment_types",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
    )

    # 2. テナントごとに is_default=TRUE を最大1件に制限する Partial Unique Index を作成
    op.create_index(
        "uix_tenant_default_employment_type",
        "employment_types",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("is_default IS TRUE"),
    )


def downgrade() -> None:
    """Downgrade schema: is_default カラムと Partial Unique Index を削除する."""
    op.drop_index(
        "uix_tenant_default_employment_type",
        table_name="employment_types",
    )
    op.drop_column("employment_types", "is_default")
