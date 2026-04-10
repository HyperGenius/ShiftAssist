"""Add index ix_shift_slots_tenant_date to shift_slots.

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2026-04-10 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "l2m3n4o5p6q7"
down_revision: str | Sequence[str] | None = "k1l2m3n4o5p6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: shift_slots テーブルに (tenant_id, date) 複合インデックスを追加する."""
    op.create_index(
        "ix_shift_slots_tenant_date",
        "shift_slots",
        ["tenant_id", "date"],
    )


def downgrade() -> None:
    """Downgrade schema: ix_shift_slots_tenant_date インデックスを削除する."""
    op.drop_index("ix_shift_slots_tenant_date", table_name="shift_slots")
