"""add tenant_skill_ranks table and migrate workers skill_rank to skill_rank_id.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-02 06:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. tenant_skill_ranks テーブルを作成
    op.create_table(
        "tenant_skill_ranks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_leader_eligible", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_tenant_skill_ranks_tenant_id",
        "tenant_skill_ranks",
        ["tenant_id"],
    )

    # 2. workers テーブルに skill_rank_id カラムを追加（まず nullable=True で追加）
    op.add_column(
        "workers",
        sa.Column(
            "skill_rank_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenant_skill_ranks.id"),
            nullable=True,
        ),
    )

    # 3. 既存の skill_rank (Enum) カラムを削除
    op.drop_column("workers", "skill_rank")

    # 4. PostgreSQL の skillrankenum 型を削除
    op.execute("DROP TYPE IF EXISTS skillrankenum")


def downgrade() -> None:
    """Downgrade schema."""
    # skillrankenum 型を再作成
    op.execute(
        "CREATE TYPE skillrankenum AS ENUM ('rank_a', 'rank_b', 'rank_c', 'rank_d')"
    )

    # workers テーブルに skill_rank カラムを再追加
    op.add_column(
        "workers",
        sa.Column(
            "skill_rank",
            postgresql.ENUM(name="skillrankenum", create_type=False),
            nullable=True,
        ),
    )

    # skill_rank_id カラムを削除
    op.drop_column("workers", "skill_rank_id")

    # tenant_skill_ranks テーブルを削除
    op.drop_index("ix_tenant_skill_ranks_tenant_id", table_name="tenant_skill_ranks")
    op.drop_table("tenant_skill_ranks")
