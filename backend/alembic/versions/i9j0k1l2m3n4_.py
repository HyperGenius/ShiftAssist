"""Add EmploymentType model and extend Worker with employment_type_id and transferred_at.

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-04-06 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i9j0k1l2m3n4"
down_revision: str | Sequence[str] | None = "h8i9j0k1l2m3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. employment_types テーブルを新設
    op.create_table(
        "employment_types",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("tenant_id", "name", name="uq_employment_type_tenant_name"),
    )
    op.create_index("ix_employment_types_tenant_id", "employment_types", ["tenant_id"])

    # 2. workers テーブルに employment_type_id カラムを追加
    op.add_column(
        "workers",
        sa.Column(
            "employment_type_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("employment_types.id"),
            nullable=True,
        ),
    )

    # 3. workers テーブルに transferred_at カラムを追加
    op.add_column(
        "workers",
        sa.Column("transferred_at", sa.Date(), nullable=True),
    )

    # 4. 既存データのマイグレーション:
    #    is_special=True の Worker に対して「特別雇用」EmploymentType を自動生成して紐付ける
    conn = op.get_bind()

    # テナントごとに is_special=True のワーカーが存在するか確認し、存在すれば「特別雇用」レコードを作成
    tenants_with_special = conn.execute(
        sa.text(
            "SELECT DISTINCT tenant_id FROM workers WHERE is_special = TRUE"
        )
    ).fetchall()

    for (tenant_id,) in tenants_with_special:
        import uuid as uuid_module

        new_id = str(uuid_module.uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO employment_types (id, tenant_id, name, created_at, updated_at) "
                "VALUES (:id, :tenant_id, :name, NOW(), NOW()) "
                "ON CONFLICT (tenant_id, name) DO NOTHING"
            ),
            {"id": new_id, "tenant_id": tenant_id, "name": "特別雇用"},
        )

        # 作成された特別雇用レコードのIDを取得して workers を更新
        result = conn.execute(
            sa.text(
                "SELECT id FROM employment_types WHERE tenant_id = :tenant_id AND name = :name"
            ),
            {"tenant_id": tenant_id, "name": "特別雇用"},
        ).fetchone()
        if result:
            employment_type_id = result[0]
            conn.execute(
                sa.text(
                    "UPDATE workers SET employment_type_id = :employment_type_id "
                    "WHERE tenant_id = :tenant_id AND is_special = TRUE"
                ),
                {
                    "employment_type_id": str(employment_type_id),
                    "tenant_id": tenant_id,
                },
            )


def downgrade() -> None:
    """Downgrade schema."""
    # workers テーブルから employment_type_id と transferred_at カラムを削除
    op.drop_column("workers", "transferred_at")
    op.drop_column("workers", "employment_type_id")

    # employment_types テーブルを削除
    op.drop_index("ix_employment_types_tenant_id", table_name="employment_types")
    op.drop_table("employment_types")
