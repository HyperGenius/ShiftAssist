# backend/app/models/models.py
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy DeclarativeBase の基底クラス."""


# --- Enums ---
class SkillRankEnum(enum.StrEnum):
    """対応者のスキルランクを表す列挙型.

    1組のペアには「rank_a」の者を1名以上含める必要がある。
    テナントをまたいで共通のビジネスルールとして適用される。

    Attributes:
        rank_a: スキルランクA（最上位）。ペアに必ず1名以上含める必要がある。
        rank_b: スキルランクB。
        rank_c: スキルランクC。
        rank_d: スキルランクD（最下位）。
    """

    rank_a = "rank_a"
    rank_b = "rank_b"
    rank_c = "rank_c"
    rank_d = "rank_d"


class PlanStatusEnum(enum.StrEnum):
    """シフトプランのステータスを表す列挙型.

    Attributes:
        draft: 下書き状態。編集中のシフトプラン。
        pending_approval: 承認待ち状態。レビュー中のシフトプラン。
        published: 公開済み状態。確定・公開されたシフトプラン。
    """

    draft = "draft"
    pending_approval = "pending_approval"
    published = "published"


class SlotTypeEnum(enum.StrEnum):
    """シフト枠の種別を表す列挙型.

    対象となる対応日と時間帯の組み合わせを定義する。
    特別雇用者は ``weekday_night`` 枠のみアサイン可能。

    Attributes:
        weekday_night: 平日夜間。
        sat_day: 土曜昼間。
        sat_night: 土曜夜間。
        sun_hol_day: 日曜・祝日昼間。
        sun_hol_night: 日曜・祝日夜間。
        long_hol_day: 長期連休（GW・シルバーウィーク・年末年始等）昼間。
        long_hol_night: 長期連休（GW・シルバーウィーク・年末年始等）夜間。
    """

    weekday_night = "weekday_night"
    sat_day = "sat_day"
    sat_night = "sat_night"
    sun_hol_day = "sun_hol_day"
    sun_hol_night = "sun_hol_night"
    long_hol_day = "long_hol_day"
    long_hol_night = "long_hol_night"


# --- Models ---
class Department(Base):
    """テナントごとに設定される所属課を表すSQLAlchemyモデル.

    DepartmentはテナントごとのビジネスデータであるためEnumではなくテーブルで管理する。
    シフト作成ルール上、同じ所属課の者を1組にしてはいけない制約がある。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナント分離に使用。
        name: 所属課の表示名（例: "1課", "East"）。
        code: 所属課の識別コード（例: "dept_1", "east"）。一意制約あり（テナント内）。
        created_at: レコード作成日時。
    """

    __tablename__ = "departments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_department_tenant_code"),
    )


class User(Base):
    """FlexShiftのユーザーを表すSQLAlchemyモデル.

    Clerk認証と連携したユーザー情報を管理する。
    ロールに応じてシフトの閲覧・編集・承認の権限が制御される。

    Attributes:
        id: UUIDによるプライマリキー。
        clerk_user_id: Clerkが発行するユーザーID。一意かつインデックス付き。
        role: ユーザーの権限ロール。``viewer`` / ``editor`` / ``approver`` のいずれか。
        created_at: レコード作成日時。
    """

    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_user_id = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, default="viewer")  # viewer, editor, approver
    created_at = Column(DateTime, default=datetime.utcnow)


class Worker(Base):
    """シフトにアサインされる対応者を表すSQLAlchemyモデル.

    マルチテナント対応のため ``tenant_id`` で論理分離される。
    特別雇用者（``is_special=True``）は平日夜間枠のみアサイン可能。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナント分離に使用。
        name: 対応者の氏名。
        department_id: 所属課のID（departmentsテーブルへのFK）。
        skill_rank: スキルランク（rank_a / rank_b / rank_c / rank_d）。
        is_special: 特別雇用者フラグ。Trueの場合、平日夜間枠のみアサイン可能。
        created_at: レコード作成日時。
        updated_at: レコード最終更新日時。更新時に自動更新される。
    """

    __tablename__ = "workers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False)  # Clerk Organization ID
    name = Column(String, nullable=False)
    department_id = Column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False
    )
    skill_rank = Column(Enum(SkillRankEnum), nullable=False)  # type: ignore[var-annotated]
    is_special = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ShiftPlan(Base):
    """月次シフトプランを表すSQLAlchemyモデル.

    テナントごとに作成される対象年月のシフト計画。
    ステータス管理により、下書き・承認待ち・公開済みの状態遷移を管理する。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナント分離に使用。
        title: シフトプランのタイトル。
        target_year_month: 対象年月。"YYYY-MM" 形式（例: "2026-04"）。
        status: シフトプランのステータス（draft / pending_approval / published）。
        created_by: 作成者のClerk User ID。
        created_at: レコード作成日時。
    """

    __tablename__ = "shift_plans"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    target_year_month = Column(String, nullable=False)  # e.g. "2026-04"
    status = Column(Enum(PlanStatusEnum), default=PlanStatusEnum.draft, nullable=False)  # type: ignore[var-annotated]
    created_by = Column(String, nullable=False)  # Clerk User ID
    created_at = Column(DateTime, default=datetime.utcnow)


class ShiftSlot(Base):
    """シフトプラン内の個別の対応枠を表すSQLAlchemyモデル.

    シフトプラン（``ShiftPlan``）に紐づく、特定の日付と枠種別の
    組み合わせを定義する。プラン削除時にカスケード削除される。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナント分離に使用。
        plan_id: 紐づくシフトプランのID。
        date: 対応日。
        slot_type: 枠の種別（平日夜間 / 土曜昼夜 / 日祝昼夜 / 長期連休昼夜）。
    """

    __tablename__ = "shift_slots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False)
    plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shift_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    date = Column(DateTime, nullable=False)  # Date型でも可
    slot_type = Column(Enum(SlotTypeEnum), nullable=False)  # type: ignore[var-annotated]


class ShiftAssignment(Base):
    """シフト枠への対応者アサインメントを表すSQLAlchemyモデル.

    シフト枠（``ShiftSlot``）と対応者（``Worker``）の対応関係を管理する。
    ルール違反があっても運用上の合意がある場合は ``is_manual_override`` フラグを立てて
    強制保存することが可能。同一枠への同一対応者の重複アサインはDB制約で防ぐ。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナント分離に使用。
        slot_id: 紐づくシフト枠のID。
        worker_id: アサインされる対応者のID。
        is_manual_override: ルール違反を承知の上で強制保存する場合にTrueを設定するフラグ。
        created_at: レコード作成日時。
    """

    __tablename__ = "shift_assignments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False)
    slot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shift_slots.id", ondelete="CASCADE"),
        nullable=False,
    )
    worker_id = Column(
        UUID(as_uuid=True), ForeignKey("workers.id", ondelete="CASCADE"), nullable=False
    )
    is_manual_override = Column(Boolean, default=False)  # ルール逸脱の強制保存フラグ
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("slot_id", "worker_id", name="uq_slot_worker"),)


class ShiftRequirementAssignment(Base):
    """シフト要件への対応者アサインメントを表すSQLAlchemyモデル.

    シフト要件（``ShiftRequirement``）と対応者（``Worker``）の対応関係を管理する。
    ルール違反があっても運用上の合意がある場合は ``is_manual_override`` フラグを立てて
    強制保存することが可能。同一要件への同一対応者の重複アサインはDB制約で防ぐ。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナント分離に使用。
        requirement_id: 紐づくシフト要件のID。
        worker_id: アサインされる対応者のID。
        is_manual_override: ルール違反を承知の上で強制保存する場合にTrueを設定するフラグ。
        created_at: レコード作成日時。
    """

    __tablename__ = "shift_requirement_assignments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False)
    requirement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shift_requirements.id", ondelete="CASCADE"),
        nullable=False,
    )
    worker_id = Column(
        UUID(as_uuid=True), ForeignKey("workers.id", ondelete="CASCADE"), nullable=False
    )
    is_manual_override = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("requirement_id", "worker_id", name="uq_req_worker"),
    )


class ShiftRequirement(Base):
    """シフト枠の必要要件を表すSQLAlchemyモデル.

    「いつ」「どの部門で」「何人のスタッフが必要か」というシフトの募集要件を定義する。
    将来的なAIによる自動アサインロジックのベースとなるデータ構造。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナント分離に使用。
        department_id: 対象部門のID（departmentsテーブルへのFK）。
        shift_date: シフト対象日。
        slot_type: 枠の種別（平日夜間 / 土曜昼夜 / 日祝昼夜 / 長期連休昼夜）。
        required_headcount: 必要人数（1以上）。
        created_at: レコード作成日時。
        updated_at: レコード最終更新日時。更新時に自動更新される。
    """

    __tablename__ = "shift_requirements"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False)
    department_id = Column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False
    )
    shift_date = Column(Date, nullable=False)
    slot_type = Column(Enum(SlotTypeEnum), nullable=False)  # type: ignore[var-annotated]
    required_headcount = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TenantRulesConfig(Base):
    """テナントごとのシフトルール設定を表すSQLAlchemyモデル.

    テナント管理者がUIから変更したシフトルールをJSONカラムとして保存する。
    レコードが存在しない場合はデフォルト値を使用する。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナントごとに一意。
        rules_json: ShiftRulesConfig の内容をJSON形式で保存。
        warnings_json: ShiftWarningsConfig の内容をJSON形式で保存。
        created_at: レコード作成日時。
        updated_at: レコード最終更新日時。更新時に自動更新される。
    """

    __tablename__ = "tenant_rules_configs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False, unique=True)
    rules_json = Column(JSON, nullable=False)
    warnings_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
