"""Add Branch, Position, LongHolidayPeriod models and extend Worker/Department.

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-04-04 06:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h8i9j0k1l2m3"
down_revision: str | Sequence[str] | None = "g7h8i9j0k1l2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. branches テーブルを新設
    op.create_table(
        "branches",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("tenant_id", "code", name="uq_branch_tenant_code"),
    )
    op.create_index("ix_branches_tenant_id", "branches", ["tenant_id"])

    # 2. positions テーブルを新設
    op.create_table(
        "positions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_excluded_from_gw", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_excluded_from_sw", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_excluded_from_year_end", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_excluded_from_all_shifts", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_positions_tenant_id", "positions", ["tenant_id"])

    # 3. long_holiday_type Enum を作成
    long_holiday_type_enum = sa.Enum(
        "gw", "sw", "year_end", name="longholidaytypeenum"
    )
    long_holiday_type_enum.create(op.get_bind(), checkfirst=True)

    # 4. long_holiday_periods テーブルを新設
    op.create_table(
        "long_holiday_periods",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column(
            "holiday_type",
            sa.Enum("gw", "sw", "year_end", name="longholidaytypeenum"),
            nullable=False,
        ),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "tenant_id",
            "holiday_type",
            "year",
            name="uq_long_holiday_period_tenant_type_year",
        ),
    )
    op.create_index(
        "ix_long_holiday_periods_tenant_id", "long_holiday_periods", ["tenant_id"]
    )

    # 5. departments テーブルに branch_id カラムを追加
    op.add_column(
        "departments",
        sa.Column(
            "branch_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("branches.id"),
            nullable=True,
        ),
    )

    # 6. transfer_type Enum を作成
    transfer_type_enum = sa.Enum(
        "no_transfer", "transfer_in", "transfer_out", name="transfertypeenum"
    )
    transfer_type_enum.create(op.get_bind(), checkfirst=True)

    # 7. workers テーブルに新規カラムを追加
    op.add_column(
        "workers",
        sa.Column("employee_code", sa.String(), nullable=True),
    )
    op.add_column(
        "workers",
        sa.Column(
            "position_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("positions.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "workers",
        sa.Column("birth_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "workers",
        sa.Column("skill_acquired_at", sa.Date(), nullable=True),
    )
    op.add_column(
        "workers",
        sa.Column(
            "transfer_type",
            sa.Enum("no_transfer", "transfer_in", "transfer_out", name="transfertypeenum"),
            nullable=True,
        ),
    )
    op.add_column(
        "workers",
        sa.Column("transfer_scheduled_month", sa.String(), nullable=True),
    )
    op.add_column(
        "workers",
        sa.Column(
            "is_cross_division_transfer", sa.Boolean(), nullable=True, server_default="false"
        ),
    )

    # (tenant_id, employee_code) のユニーク制約を追加
    op.create_unique_constraint(
        "uq_worker_tenant_employee_code",
        "workers",
        ["tenant_id", "employee_code"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # workers テーブルの変更を元に戻す
    op.drop_constraint("uq_worker_tenant_employee_code", "workers", type_="unique")
    op.drop_column("workers", "is_cross_division_transfer")
    op.drop_column("workers", "transfer_scheduled_month")
    op.drop_column("workers", "transfer_type")
    op.drop_column("workers", "skill_acquired_at")
    op.drop_column("workers", "birth_date")
    op.drop_column("workers", "position_id")
    op.drop_column("workers", "employee_code")

    # departments テーブルの変更を元に戻す
    op.drop_column("departments", "branch_id")

    # long_holiday_periods テーブルを削除
    op.drop_index("ix_long_holiday_periods_tenant_id", table_name="long_holiday_periods")
    op.drop_table("long_holiday_periods")

    # positions テーブルを削除
    op.drop_index("ix_positions_tenant_id", table_name="positions")
    op.drop_table("positions")

    # branches テーブルを削除
    op.drop_index("ix_branches_tenant_id", table_name="branches")
    op.drop_table("branches")

    # Enum 型を削除
    sa.Enum(name="longholidaytypeenum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="transfertypeenum").drop(op.get_bind(), checkfirst=True)
