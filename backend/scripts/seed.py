# backend/scripts/seed.py
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# backend/ ディレクトリをパスに追加して app モジュールを参照できるようにする
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# モデルとEnumのインポート
from app.models.models import (
    Department,
    PlanStatusEnum,
    ShiftAssignment,
    ShiftPlan,
    ShiftSlot,
    SkillRankEnum,
    SlotTypeEnum,
    User,
    Worker,
)

# .envの読み込み
load_dotenv()

DATABASE_URL = os.getenv("NEON_DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("NEON_DATABASE_URLが設定されていません。")

# DBエンジンの作成
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed_data():
    """ダミーデータをDBに投入する."""
    db = SessionLocal()
    try:
        print("🌱 既存のデータをクリアしています...")
        # 外部キー制約があるため、子テーブルから順に削除
        db.query(ShiftAssignment).delete()
        db.query(ShiftSlot).delete()
        db.query(ShiftPlan).delete()
        db.query(Worker).delete()
        db.query(Department).delete()
        db.query(User).delete()
        db.commit()

        print("🌱 ダミーデータを投入しています...")

        # 1. テナントとユーザーの作成 (Clerkを想定したダミーID)
        dummy_tenant_id = "org_dummy_12345"

        user1 = User(clerk_user_id="user_dummy_admin", role="editor")
        user2 = User(clerk_user_id="user_dummy_viewer", role="viewer")
        db.add_all([user1, user2])

        # 2. 所属課 (Department) の作成
        departments = [
            Department(tenant_id=dummy_tenant_id, name="A課", code="dept_a"),
            Department(tenant_id=dummy_tenant_id, name="B課", code="dept_b"),
            Department(tenant_id=dummy_tenant_id, name="C課", code="dept_c"),
        ]
        db.add_all(departments)
        db.commit()  # IDを確定させるために一度コミット

        # 3. 対応者 (Worker) の作成
        # ルール検証のテストができるよう、様々なパターンのスタッフを用意
        workers = [
            Worker(
                tenant_id=dummy_tenant_id,
                name="佐藤 太郎",
                department_id=departments[0].id,
                skill_rank=SkillRankEnum.rank_a,
            ),
            Worker(
                tenant_id=dummy_tenant_id,
                name="鈴木 次郎",
                department_id=departments[1].id,
                skill_rank=SkillRankEnum.rank_b,
            ),
            Worker(
                tenant_id=dummy_tenant_id,
                name="高橋 三郎",
                department_id=departments[2].id,
                skill_rank=SkillRankEnum.rank_a,
            ),
            Worker(
                tenant_id=dummy_tenant_id,
                name="田中 四郎",
                department_id=departments[0].id,
                skill_rank=SkillRankEnum.rank_c,
            ),
            Worker(
                tenant_id=dummy_tenant_id,
                name="伊藤 花子",
                department_id=departments[1].id,
                skill_rank=SkillRankEnum.rank_d,
            ),
            Worker(
                tenant_id=dummy_tenant_id,
                name="渡辺 特別",
                department_id=departments[2].id,
                skill_rank=SkillRankEnum.rank_a,
                is_special=True,
            ),  # 平日夜間のみ
        ]
        db.add_all(workers)
        db.commit()  # IDを確定させるために一度コミット

        # 4. シフト計画 (ShiftPlan) の作成
        plan = ShiftPlan(
            tenant_id=dummy_tenant_id,
            title="2026年4月度シフト",
            target_year_month="2026-04",
            status=PlanStatusEnum.draft,
            created_by=user1.clerk_user_id,
        )
        db.add(plan)
        db.commit()

        # 5. シフト枠 (ShiftSlot) の作成 (4月の数日分をサンプルとして作成)
        slots = [
            ShiftSlot(
                tenant_id=dummy_tenant_id,
                plan_id=plan.id,
                date=datetime(2026, 4, 1),
                slot_type=SlotTypeEnum.weekday_night,
            ),
            ShiftSlot(
                tenant_id=dummy_tenant_id,
                plan_id=plan.id,
                date=datetime(2026, 4, 4),
                slot_type=SlotTypeEnum.sat_day,
            ),
            ShiftSlot(
                tenant_id=dummy_tenant_id,
                plan_id=plan.id,
                date=datetime(2026, 4, 4),
                slot_type=SlotTypeEnum.sat_night,
            ),
        ]
        db.add_all(slots)
        db.commit()

        # 6. シフト割り当て (ShiftAssignment) の作成
        # 枠1 (4/1 平日夜間): 佐藤(A課/rank_a) & 鈴木(B課/rank_b) -> 正常パターン
        assign1 = ShiftAssignment(
            tenant_id=dummy_tenant_id, slot_id=slots[0].id, worker_id=workers[0].id
        )
        assign2 = ShiftAssignment(
            tenant_id=dummy_tenant_id, slot_id=slots[0].id, worker_id=workers[1].id
        )

        # 枠2 (4/4 土曜昼間): 高橋(C課/rank_a) & 伊藤(B課/rank_d) -> 正常パターン
        assign3 = ShiftAssignment(
            tenant_id=dummy_tenant_id, slot_id=slots[1].id, worker_id=workers[2].id
        )
        assign4 = ShiftAssignment(
            tenant_id=dummy_tenant_id, slot_id=slots[1].id, worker_id=workers[4].id
        )

        # 枠3 (4/4 土曜夜間): 佐藤(A課/rank_a) & 田中(A課/rank_c) -> 【ルール違反を強制保存するテスト用】
        # A課同士なので本来はエラーだが、is_manual_override=Trueで保存したケース
        assign5 = ShiftAssignment(
            tenant_id=dummy_tenant_id,
            slot_id=slots[2].id,
            worker_id=workers[0].id,
            is_manual_override=True,
        )
        assign6 = ShiftAssignment(
            tenant_id=dummy_tenant_id,
            slot_id=slots[2].id,
            worker_id=workers[3].id,
            is_manual_override=True,
        )

        db.add_all([assign1, assign2, assign3, assign4, assign5, assign6])
        db.commit()

        print("✨ シードデータの投入が完了しました！")

    except Exception as e:
        db.rollback()
        print(f"❌ エラーが発生しました: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
