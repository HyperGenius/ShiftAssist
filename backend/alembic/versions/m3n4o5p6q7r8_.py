"""Add sat_pre_hol_night to slottypeenum.

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2026-04-10 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "m3n4o5p6q7r8"
down_revision: str | Sequence[str] | None = "l2m3n4o5p6q7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# PostgreSQL の ENUM ADD VALUE は DDL トランザクション内で実行できないため、
# transaction_per_migration を False に設定する必要がある。
transaction_per_migration = False


def upgrade() -> None:
    """Upgrade schema: slottypeenum に sat_pre_hol_night を追加する."""
    op.execute("ALTER TYPE slottypeenum ADD VALUE IF NOT EXISTS 'sat_pre_hol_night'")


def downgrade() -> None:
    """Downgrade schema: PostgreSQL では ENUM の値削除は直接サポートされないため何もしない.

    本番環境でのダウングレードが必要な場合は、型の再作成が必要。
    """
    pass
