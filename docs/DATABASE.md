# データベース設計方針

本プロジェクトでは、データベース（PostgreSQL）のスキーマ管理はバックエンドの `alembic` マイグレーションファイルを正とする。
本ドキュメントでは、全体的な設計方針と主要なテーブルの役割（概念モデル）のみを定義する。

## 1. 全体設計方針

* **マルチテナント (論理分離)**:
  * ほぼ全てのテーブルに `tenant_id` (VARCHAR: ClerkのOrganization ID) を付与する。
  * バックエンドのORM (SQLAlchemy等) レベルで、常に `WHERE tenant_id = ?` が付与されるように設計し、データ漏洩を強固に防ぐ。
* **ID体系**: プライマリキーは `UUID` (v4) を標準とする。
* **人間の判断の尊重 (オーバーライド)**: 「当人同士の合意によるシフト交換」など、システム上のルール（中9日空きなど）を逸脱しても、作成者や承認者が妥当と判断した場合はそれを許容できる（強制保存できる）データ構造とする。

## 2. 主要テーブル一覧と役割

### テナント・ユーザー・権限関連
* **`tenants` (テナント情報)** ※オプション
  * `tenant_id` (PK, Clerk Organization ID) を持ち、テナント固有の設定（例: カスタムルールのON/OFFなど）を保存する。
* **`users` (システムユーザー)**
  * ClerkのユーザーIDと紐付く。テナントとの紐付けはClerk側に依存するが、アプリ内での特定のユーザー設定を持つために用意。
  * ロール（`viewer`: 閲覧者, `editor`: 作成者, `approver`: 承認者）を保持し、機能へのアクセス制御を行う。
* **`workers` (対応者マスタ)**
  * `tenant_id` を保持。あるテナント（企業）に所属するスタッフの属性を管理。
  * シフトにアサインされるスタッフの属性（所属課、スキルランク、特別雇用者フラグなど）を管理する。
  * 閲覧者が自分のシフトを確認できるよう、`users` テーブルと紐付け（1対1または1対0）を持たせる。

### シフト管理関連
* **`shift_plans` (シフト計画)**
  * 「2026年4月度」などの月次単位のシフト表全体を管理する。
  * 承認フローを見据え、ステータス（`draft`: 下書き, `pending_approval`: 承認待ち, `published`: 確定）を持たせる。
* **`shift_slots` (シフト枠)**
  * 計画内の「1日・1枠（例: 4/4 土曜夜間）」を表すエンティティ。
* **`shift_assignments` (シフト割り当て)**
  * どの「枠 (`shift_slots`)」に誰 (`workers`) が入るかという交差テーブル。
  * **手動オーバーライドフラグ (`is_manual_override`)** 等を持たせ、ルール違反があっても合意の上でアサインされた（警告を無視して確定した）ことをシステム的に記録・許容できるようにする。

### シフト要件（スナップショット）関連

* **`shift_requirements` (シフト要件スナップショット)**
  * 各日・各枠で「何人必要か」という要件をスナップショットとして永続化するテーブル。
  * 将来的な要件ルールの変更（例: 来月から必要人数が増える等）が過去データに影響を与えないよう、DBに保存する。

  | カラム | 型 | 説明 |
  |---|---|---|
  | `id` | UUID | プライマリキー |
  | `tenant_id` | String | テナント識別子（Clerk Organization ID） |
  | `department_id` | UUID (nullable) | 対象部門ID（`departments` テーブルへのFK）。スナップショット生成時はNULL可。 |
  | `shift_date` | Date | シフト対象日 |
  | `slot_type` | Enum (`SlotTypeEnum`) | 枠の種別（`weekday_night` / `sat_day` / `sat_night` / `sun_hol_day` / `sun_hol_night` / `long_hol_day` / `long_hol_night`） |
  | `required_headcount` | Integer | 必要人数（1以上）。デフォルト: 2 |
  | `created_at` | DateTime | レコード作成日時 |
  | `updated_at` | DateTime | レコード最終更新日時 |

  - `(tenant_id, shift_date, slot_type)` に一意制約 `uq_shift_req_tenant_date_slot` を設定し、重複登録をDBレベルで防止する。
  - テナントのインデックス `ix_shift_requirements_tenant_id` を設定済み。

* **`shift_requirement_assignments` (シフト要件アサイン)**
  * どの `shift_requirements` に誰 (`workers`) が割り当てられているかを管理する交差テーブル。

  | カラム | 型 | 説明 |
  |---|---|---|
  | `id` | UUID | プライマリキー |
  | `tenant_id` | String | テナント識別子 |
  | `requirement_id` | UUID | `shift_requirements.id` への FK（CASCADE DELETE） |
  | `worker_id` | UUID | `workers.id` への FK |
  | `is_manual_override` | Boolean | 手動オーバーライドフラグ（ルール違反を承知の上でのアサイン） |
  | `created_at` | DateTime | レコード作成日時 |

  - `(requirement_id, worker_id)` に一意制約 `uq_req_worker` を設定。
  - テナントのインデックス `ix_shift_requirement_assignments_tenant_id` を設定済み。
