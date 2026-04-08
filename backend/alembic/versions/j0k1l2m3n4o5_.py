"""Add unique constraint and make department_id nullable in shift_requirements.

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-04-08 00:00:00.000000

"""

from collections.abc import Sequence

from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "j0k1l2m3n4o5"
down_revision: str | Sequence[str] | None = "i9j0k1l2m3n4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. department_id を nullable に変更（スナップショット生成時に部門指定が不要なため）
    op.alter_column(
        "shift_requirements",
        "department_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    # 2. (tenant_id, shift_date, slot_type) のユニーク制約を追加（スナップショット重複防止）
    op.create_unique_constraint(
        "uq_shift_req_tenant_date_slot",
        "shift_requirements",
        ["tenant_id", "shift_date", "slot_type"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_shift_req_tenant_date_slot", "shift_requirements", type_="unique"
    )
    op.alter_column(
        "shift_requirements",
        "department_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
