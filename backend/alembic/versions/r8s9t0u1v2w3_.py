"""Add is_assign_prohibited to custom_rules.

Revision ID: r8s9t0u1v2w3
Revises: q7r8s9t0u1v2
Create Date: 2026-04-20 07:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "r8s9t0u1v2w3"
down_revision: str | Sequence[str] | None = "q7r8s9t0u1v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: custom_rules テーブルに is_assign_prohibited カラムを追加する."""
    op.add_column(
        "custom_rules",
        sa.Column(
            "is_assign_prohibited",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    """Downgrade schema: custom_rules テーブルから is_assign_prohibited カラムを削除する."""
    op.drop_column("custom_rules", "is_assign_prohibited")
