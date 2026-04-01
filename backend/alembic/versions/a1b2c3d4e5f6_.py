"""add shift_requirements table.

Revision ID: a1b2c3d4e5f6
Revises: 6e1a6cbb2181
Create Date: 2026-04-01 04:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "6e1a6cbb2181"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "shift_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shift_date", sa.Date(), nullable=False),
        sa.Column(
            "slot_type",
            postgresql.ENUM(name="slottypeenum", create_type=False),
            nullable=False,
        ),
        sa.Column("required_headcount", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
    )
    op.create_index(
        "ix_shift_requirements_tenant_id", "shift_requirements", ["tenant_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_shift_requirements_tenant_id", table_name="shift_requirements")
    op.drop_table("shift_requirements")
