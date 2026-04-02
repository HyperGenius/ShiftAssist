"""add deleted_at to departments and partial unique index.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-02 04:39:52.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # deleted_at カラムを追加
    op.add_column(
        "departments",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 既存のUNIQUE制約を削除（全レコード対象の制約）
    op.drop_constraint("uq_department_tenant_code", "departments", type_="unique")

    # 有効レコード（deleted_at IS NULL）のみに適用する部分インデックスを作成
    op.create_index(
        "uq_department_tenant_code_active",
        "departments",
        ["tenant_id", "code"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # 部分インデックスを削除
    op.drop_index("uq_department_tenant_code_active", table_name="departments")

    # 全レコード対象のUNIQUE制約を再作成
    op.create_unique_constraint(
        "uq_department_tenant_code", "departments", ["tenant_id", "code"]
    )

    # deleted_at カラムを削除
    op.drop_column("departments", "deleted_at")
