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
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy DeclarativeBase の基底クラス."""


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
        sat_pre_hol_night: 土曜・祝前日夜間。金曜日または翌日が祝日となる平日の夜間。
    """

    weekday_night = "weekday_night"
    sat_day = "sat_day"
    sat_night = "sat_night"
    sun_hol_day = "sun_hol_day"
    sun_hol_night = "sun_hol_night"
    long_hol_day = "long_hol_day"
    long_hol_night = "long_hol_night"
    sat_pre_hol_night = "sat_pre_hol_night"


class LongHolidayTypeEnum(enum.StrEnum):
    """長期休暇の種別を表す列挙型.

    Attributes:
        gw: ゴールデンウィーク。
        sw: シルバーウィーク。
        year_end: 年末年始。
    """

    gw = "gw"
    sw = "sw"
    year_end = "year_end"


class TransferTypeEnum(enum.StrEnum):
    """異動種別を表す列挙型.

    Attributes:
        no_transfer: 異動なし。
        transfer_in: 転入（他所属からの異動）。
        transfer_out: 転出（他所属への異動）。
        hired: 採用（新規雇用）。
    """

    no_transfer = "no_transfer"
    transfer_in = "transfer_in"
    transfer_out = "transfer_out"
    hired = "hired"


# --- Models ---
class Branch(Base):
    """テナントごとに設定される上位組織（支所等）を表すSQLAlchemyモデル.

    Departmentの上位階層として機能し、組織の階層構造を管理する。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナント分離に使用。
        name: 上位組織の表示名（例: "本所", "第一支所"）。
        code: 上位組織の識別コード（例: "branch_1", "main"）。一意制約あり（テナント内）。
        created_at: レコード作成日時。
    """

    __tablename__ = "branches"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_branch_tenant_code"),
    )


class Position(Base):
    """テナントごとに設定される役職マスタを表すSQLAlchemyモデル.

    除外フラグにより長期休暇期間中のアサイン可否を制御する。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナント分離に使用。
        name: 役職名（例: "係長", "主任"）。
        is_excluded_from_gw: GWアサイン除外フラグ。
        is_excluded_from_sw: SWアサイン除外フラグ。
        is_excluded_from_year_end: 年末年始アサイン除外フラグ。
        is_excluded_from_all_shifts: 原則アサイン対象外フラグ。
        created_at: レコード作成日時。
    """

    __tablename__ = "positions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    is_excluded_from_gw = Column(Boolean, nullable=False, default=False)
    is_excluded_from_sw = Column(Boolean, nullable=False, default=False)
    is_excluded_from_year_end = Column(Boolean, nullable=False, default=False)
    is_excluded_from_all_shifts = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Department(Base):
    """テナントごとに設定される所属課を表すSQLAlchemyモデル.

    DepartmentはテナントごとのビジネスデータであるためEnumではなくテーブルで管理する。
    シフト作成ルール上、同じ所属課の者を1組にしてはいけない制約がある。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナント分離に使用。
        name: 所属課の表示名（例: "1課", "East"）。
        code: 所属課の識別コード（例: "dept_1", "east"）。一意制約あり（テナント内、有効レコードのみ）。
        branch_id: 上位組織（支所等）のID（branchesテーブルへのFK）。任意。
        created_at: レコード作成日時。
        deleted_at: 論理削除日時。NULLの場合は有効なレコード。
    """

    __tablename__ = "departments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

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


class TenantSkillRank(Base):
    """テナントごとのスキルランクマスタを表すSQLAlchemyモデル.

    テナント管理者が任意の名称・数でスキルランクをカスタマイズできる。
    ``is_leader_eligible`` フラグにより、シフト制約（最上位ランクを必ず1名含む）を抽象化する。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナント分離に使用。
        name: スキルランクの表示名（例: "A", "1級", "シニア"）。
        sort_order: 表示順序（昇順で並べる）。
        is_leader_eligible: リーダー適性フラグ。Trueの場合、シフトペアに必ず1名含める必要がある。
        created_at: レコード作成日時。
    """

    __tablename__ = "tenant_skill_ranks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    is_leader_eligible = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class EmploymentType(Base):
    """テナントごとの雇用形態マスタを表すSQLAlchemyモデル.

    テナント管理者が任意の名称で雇用形態を定義できる。
    Worker の ``employment_type_id`` FK により雇用形態を紐付ける。
    ``is_default=True`` の雇用形態はテナント内のデフォルト（正職員等）として扱われ、
    1テナントにつき最大1件まで設定可能。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナント分離に使用。
        name: 雇用形態の表示名（例: "正職員", "非常勤", "特別雇用"）。
        is_default: テナント内のデフォルト雇用形態フラグ。テナントごとに最大1件。
        created_at: レコード作成日時。
        updated_at: レコード最終更新日時。更新時に自動更新される。
    """

    __tablename__ = "employment_types"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_employment_type_tenant_name"),
        Index(
            "uix_tenant_default_employment_type",
            "tenant_id",
            unique=True,
            postgresql_where=text("is_default IS TRUE"),
        ),
    )


class EmploymentTypeRule(Base):
    """雇用形態別シフトルールを表すSQLAlchemyモデル.

    雇用形態（EmploymentType）ごとにアサイン制約を上書き設定するためのテーブル。
    ``employment_type_id`` に対して1対1の関係を持つ。

    Attributes:
        id: UUIDによるプライマリキー。
        employment_type_id: 対象の雇用形態ID（employment_typesテーブルへのFK、1対1）。
        tenant_id: Clerk OrganizationのID。テナント分離・インデックス用。
        require_default_pair: True の場合、同一枠のペアにデフォルト雇用形態のWorkerが必須。
        allowed_slot_types: アサイン可能なSlotTypeEnumのリスト（空/nullは制限なし）。
        annual_limit_overrides: AnnualShiftLimitsConfig の部分的な上書き設定（各キーはnull許容）。
        created_at: レコード作成日時。
        updated_at: レコード最終更新日時。更新時に自動更新される。
    """

    __tablename__ = "employment_type_rules"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employment_type_id = Column(
        UUID(as_uuid=True),
        ForeignKey("employment_types.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id = Column(String, index=True, nullable=False)
    require_default_pair = Column(Boolean, default=False, nullable=False)
    allowed_slot_types = Column(JSON, nullable=True)
    annual_limit_overrides = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "employment_type_id", name="uq_employment_type_rule_employment_type_id"
        ),
    )


class CustomRule(Base):
    """Worker単位のカスタムシフトルールを表すSQLAlchemyモデル.

    テナント管理者が任意の名称でカスタムルールを作成し、Worker単位でアサインできる。
    雇用形態ルール・グローバルルールより優先して適用される。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナント分離・インデックス用。
        name: カスタムルールの表示名。テナント内で一意。
        allowed_slot_types: アサイン可能なSlotTypeEnumのリスト（空/nullは制限なし）。
        annual_limit_overrides: AnnualShiftLimitsConfig の部分的な上書き設定（各キーはnull許容）。
        is_assign_prohibited: アサイン不可フラグ。Trueの場合、全スロットへのアサインを禁止する。
        created_at: レコード作成日時。
        updated_at: レコード最終更新日時。更新時に自動更新される。
    """

    __tablename__ = "custom_rules"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    allowed_slot_types = Column(JSON, nullable=True)
    annual_limit_overrides = Column(JSON, nullable=True)
    is_assign_prohibited = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_custom_rule_tenant_name"),
    )


class Worker(Base):
    """シフトにアサインされる対応者を表すSQLAlchemyモデル.

    マルチテナント対応のため ``tenant_id`` で論理分離される。
    特別雇用者（``is_special=True``）は平日夜間枠のみアサイン可能。
    ``employment_type_id`` により雇用形態マスタと紐付く。
    ``custom_rule_id`` によりWorker単位のカスタムルールを設定できる。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナント分離に使用。
        employee_no: 社員番号。バルクUpsertのキーとして使用。テナント内で一意（NULL許容）。
        employee_code: 職員番号。テナント内で一意（NULL許容）。
        name: 対応者の氏名。
        department_id: 所属課のID（departmentsテーブルへのFK）。
        skill_rank_id: スキルランクのID（tenant_skill_ranksテーブルへのFK）。
        position_id: 役職のID（positionsテーブルへのFK）。任意。
        employment_type_id: 雇用形態のID（employment_typesテーブルへのFK）。任意。
        custom_rule_id: カスタムルールのID（custom_rulesテーブルへのFK、ON DELETE SET NULL）。任意。
        is_special: 特別雇用者フラグ（非推奨。employment_type.is_default による判定に移行済み）。
        birth_date: 生年月日（年齢計算用）。
        skill_acquired_at: 現在のスキルランクの取得日。
        transfer_type: 異動種別。
        transfer_scheduled_month: 異動予定月（YYYY-MM形式）。
        is_cross_division_transfer: 事業本部間異動フラグ。
        joined_at: 着任日（新人・異動者の期間制限判定、統計正規化に使用）。
        transferred_at: 異動日（異動後3ヶ月経過判定に使用）。
        created_at: レコード作成日時。
        updated_at: レコード最終更新日時。更新時に自動更新される。
    """

    __tablename__ = "workers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False)  # Clerk Organization ID
    employee_no = Column(String, nullable=True)  # 社員番号（バルクUpsertキー）
    employee_code = Column(String, nullable=True)  # 職員番号
    name = Column(String, nullable=False)
    department_id = Column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False
    )
    skill_rank_id = Column(
        UUID(as_uuid=True), ForeignKey("tenant_skill_ranks.id"), nullable=False
    )
    position_id = Column(UUID(as_uuid=True), ForeignKey("positions.id"), nullable=True)
    employment_type_id = Column(
        UUID(as_uuid=True), ForeignKey("employment_types.id"), nullable=True
    )  # 雇用形態ID（employment_typesテーブルへのFK）
    custom_rule_id = Column(
        UUID(as_uuid=True),
        ForeignKey("custom_rules.id", ondelete="SET NULL"),
        nullable=True,
    )  # カスタムルールID（custom_rulesテーブルへのFK、削除時にNULL）
    is_special = Column(Boolean, default=False)  # 後方互換性フラグ
    birth_date = Column(Date, nullable=True)  # 生年月日（年齢計算用）
    skill_acquired_at = Column(Date, nullable=True)  # スキルランク取得日
    transfer_type = Column(Enum(TransferTypeEnum), nullable=True)  # type: ignore[var-annotated]
    transfer_scheduled_month = Column(String, nullable=True)  # 異動予定月 YYYY-MM
    is_cross_division_transfer = Column(
        Boolean, nullable=True, default=False
    )  # 事業本部間異動
    joined_at = Column(Date, nullable=True)  # 着任日（統計正規化に使用）
    transferred_at = Column(Date, nullable=True)  # 異動日（異動後3ヶ月経過判定）
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "employee_no", name="uq_worker_tenant_employee_no"
        ),
        UniqueConstraint(
            "tenant_id", "employee_code", name="uq_worker_tenant_employee_code"
        ),
    )


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

    __table_args__ = (
        Index(
            "ix_shift_plans_tenant_status_month",
            "tenant_id",
            "status",
            "target_year_month",
        ),
    )


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

    __table_args__ = (Index("ix_shift_slots_tenant_date", "tenant_id", "date"),)


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

    __table_args__ = (
        UniqueConstraint("slot_id", "worker_id", name="uq_slot_worker"),
        Index("ix_shift_assignments_worker_slot", "worker_id", "slot_id"),
    )


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
    スナップショットとして永続化することで、要件ルール変更が過去データに影響しないよう設計。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナント分離に使用。
        department_id: 対象部門のID（departmentsテーブルへのFK）。スナップショット生成時はNULL可。
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
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True
    )
    shift_date = Column(Date, nullable=False)
    slot_type = Column(Enum(SlotTypeEnum), nullable=False)  # type: ignore[var-annotated]
    required_headcount = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "shift_date", "slot_type", name="uq_shift_req_tenant_date_slot"
        ),
    )


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


class TenantHoliday(Base):
    """テナントごとの祝日・休日データを表すSQLAlchemyモデル.

    テナント管理者が独自の祝日（創立記念日等）を登録・管理する。
    対象年のデータが未登録の場合は ``jpholiday`` を用いて日本の標準祝日を自動投入する。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナント分離に使用。
        date: 祝日・休日の日付。
        name: 祝日・休日の名称（例: "元日", "創立記念日"）。
        is_long_holiday: 長期連休フラグ。GW・年末年始等の場合はTrue。
        created_at: レコード作成日時。
    """

    __tablename__ = "tenant_holidays"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False)
    date = Column(Date, nullable=False)
    name = Column(String, nullable=False)
    is_long_holiday = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "date", name="uq_tenant_holiday_date"),
    )


class TenantStatsConfig(Base):
    """テナントごとの統計集計設定を表すSQLAlchemyモデル.

    テナント管理者が統計の集計対象期間を設定する。
    レコードが存在しない場合はデフォルト値（12ヶ月）を使用する。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナントごとに一意。
        stats_period_months: 統計集計対象期間（月数）。デフォルトは12ヶ月。
        created_at: レコード作成日時。
        updated_at: レコード最終更新日時。更新時に自動更新される。
    """

    __tablename__ = "tenant_stats_configs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False, unique=True)
    stats_period_months = Column(Integer, nullable=False, default=12)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LongHolidayPeriod(Base):
    """テナントごとの長期休暇期間設定を表すSQLAlchemyモデル.

    管理者が年度ごとにGW・SW・年末年始の具体的な開始・終了日を設定する。
    役職の除外フラグと組み合わせてアサイン可否を判定するために使用する。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナント分離に使用。
        holiday_type: 長期休暇の種別（gw / sw / year_end）。
        year: 対象年（例: 2026）。
        start_date: 長期休暇の開始日。
        end_date: 長期休暇の終了日。
        created_at: レコード作成日時。
        updated_at: レコード最終更新日時。更新時に自動更新される。
    """

    __tablename__ = "long_holiday_periods"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False)
    holiday_type = Column(Enum(LongHolidayTypeEnum), nullable=False)  # type: ignore[var-annotated]
    year = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "holiday_type",
            "year",
            name="uq_long_holiday_period_tenant_type_year",
        ),
    )


class WorkerMonthlySlotStats(Base):
    """ワーカー月次シフト枠種別集計テーブルを表すSQLAlchemyモデル.

    ``published`` 状態のシフトプランを元に、ワーカーごと・年月ごと・枠種別ごとの
    シフト回数を集計して保存する。スマートサジェスト機能でも再利用する。

    Attributes:
        id: UUIDによるプライマリキー。
        tenant_id: Clerk OrganizationのID。テナント分離に使用。
        worker_id: 集計対象ワーカーのID（workersテーブルへのFK）。
        year_month: 集計対象年月（YYYY-MM形式）。
        slot_type: 枠の種別（SlotTypeEnum）。
        weekday: 曜日（0=月〜3=木）。``weekday_night`` 以外は NULL。
        count: シフト回数。
        updated_at: レコード最終更新日時。
    """

    __tablename__ = "worker_monthly_slot_stats"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, index=True, nullable=False)
    worker_id = Column(
        UUID(as_uuid=True), ForeignKey("workers.id", ondelete="CASCADE"), nullable=False
    )
    year_month = Column(String, nullable=False)  # YYYY-MM
    slot_type = Column(Enum(SlotTypeEnum), nullable=False)  # type: ignore[var-annotated]
    weekday = Column(Integer, nullable=True)  # 0=月〜3=木, weekday_night以外はNULL
    count = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "worker_id",
            "year_month",
            "slot_type",
            "weekday",
            name="uq_worker_monthly_slot_stats",
        ),
        Index("ix_worker_monthly_slot_stats_tenant_ym", "tenant_id", "year_month"),
    )
