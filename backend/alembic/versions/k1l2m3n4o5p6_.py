"""Add hired value to transfertypeenum.

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
Create Date: 2026-04-09 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "k1l2m3n4o5p6"
down_revision: str | Sequence[str] | None = "j0k1l2m3n4o5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: transfertypeenum に 'hired' 値を追加する."""
    op.execute("ALTER TYPE transfertypeenum ADD VALUE IF NOT EXISTS 'hired'")


def downgrade() -> None:
    """Downgrade schema.

    PostgreSQL の ENUM 型から値を削除するには pg_enum を直接操作する必要がある。
    ダウングレード前に 'hired' を使用しているレコードが存在しないことを確認すること。

    手順（psql で手動実行）:
        -- 事前確認
        SELECT COUNT(*) FROM workers WHERE transfer_type = 'hired';
        -- 0件であることを確認してから実行
        DELETE FROM pg_enum
        WHERE enumlabel = 'hired'
          AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'transfertypeenum');
    """
    pass
