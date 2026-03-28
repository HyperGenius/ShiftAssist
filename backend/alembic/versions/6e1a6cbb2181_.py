"""initial schema.

Revision ID: 6e1a6cbb2181
Revises:
Create Date: 2026-03-28 16:40:25.625666

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6e1a6cbb2181"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enum types (explicit DDL to avoid SQLAlchemy auto-create conflicts)
    op.execute(
        sa.text(
            "CREATE TYPE skillrankenum AS ENUM ('rank_a', 'rank_b', 'rank_c', 'rank_d')"
        )
    )
    op.execute(
        sa.text(
            "CREATE TYPE planstatusenum AS ENUM ('draft', 'pending_approval', 'published')"
        )
    )
    op.execute(
        sa.text(
            "CREATE TYPE slottypeenum AS ENUM "
            "('weekday_night', 'sat_day', 'sat_night', "
            "'sun_hol_day', 'sun_hol_night', 'long_hol_day', 'long_hol_night')"
        )
    )

    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("tenant_id", "code", name="uq_department_tenant_code"),
    )
    op.create_index("ix_departments_tenant_id", "departments", ["tenant_id"])

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clerk_user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("clerk_user_id", name="uq_users_clerk_user_id"),
    )
    op.create_index("ix_users_clerk_user_id", "users", ["clerk_user_id"], unique=True)

    op.create_table(
        "workers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "skill_rank",
            postgresql.ENUM(name="skillrankenum", create_type=False),
            nullable=False,
        ),
        sa.Column("is_special", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
    )
    op.create_index("ix_workers_tenant_id", "workers", ["tenant_id"])

    op.create_table(
        "shift_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("target_year_month", sa.String(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="planstatusenum", create_type=False),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_shift_plans_tenant_id", "shift_plans", ["tenant_id"])

    op.create_table(
        "shift_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column(
            "slot_type",
            postgresql.ENUM(name="slottypeenum", create_type=False),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["shift_plans.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_shift_slots_tenant_id", "shift_slots", ["tenant_id"])

    op.create_table(
        "shift_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("slot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_manual_override", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["slot_id"], ["shift_slots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("slot_id", "worker_id", name="uq_slot_worker"),
    )
    op.create_index(
        "ix_shift_assignments_tenant_id", "shift_assignments", ["tenant_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_shift_assignments_tenant_id", table_name="shift_assignments")
    op.drop_table("shift_assignments")

    op.drop_index("ix_shift_slots_tenant_id", table_name="shift_slots")
    op.drop_table("shift_slots")

    op.drop_index("ix_shift_plans_tenant_id", table_name="shift_plans")
    op.drop_table("shift_plans")

    op.drop_index("ix_workers_tenant_id", table_name="workers")
    op.drop_table("workers")

    op.drop_index("ix_users_clerk_user_id", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_departments_tenant_id", table_name="departments")
    op.drop_table("departments")

    op.execute(sa.text("DROP TYPE slottypeenum"))
    op.execute(sa.text("DROP TYPE planstatusenum"))
    op.execute(sa.text("DROP TYPE skillrankenum"))
