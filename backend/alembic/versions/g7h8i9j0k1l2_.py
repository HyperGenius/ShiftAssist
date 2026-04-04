"""add employee_no to workers table for bulk upsert support.

Revision ID: g7h8i9j0k1l2
Revises: a2b3c4d5e6f7
Create Date: 2026-04-04 02:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g7h8i9j0k1l2"
down_revision: str | Sequence[str] | None = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # workers テーブルに employee_no カラムを追加（バルクUpsertキー）
    op.add_column(
        "workers",
        sa.Column("employee_no", sa.String(), nullable=True),
    )

    # (tenant_id, employee_no) のユニーク制約を追加
    # NULLは一意制約の対象外（PostgreSQLの標準動作）
    op.create_unique_constraint(
        "uq_worker_tenant_employee_no",
        "workers",
        ["tenant_id", "employee_no"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # ユニーク制約を削除
    op.drop_constraint(
        "uq_worker_tenant_employee_no",
        "workers",
        type_="unique",
    )

    # employee_no カラムを削除
    op.drop_column("workers", "employee_no")
