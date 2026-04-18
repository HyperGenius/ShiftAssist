# Agent.md - AI Agent Guidelines
このドキュメントは、本プロジェクト（ShiftAssist）の開発を担当するAI Agent（GitHub Copilot Agent等）に向けたコーディング規約、テスト方針を定義するものです。

## 1. 技術スタック (Tech Stack)

### Backend

* **Language**: Python 3.11
* **Framework**: FastAPI
* **Lint/Format**: Ruff, Mypy
* **Testing**: Pytest

### Frontend

* **Framework**: Next.js 15+ (App Router)
* **Language**: TypeScript
* **Styling**: Tailwind CSS
* **UI Library**: カスタムUIコンポーネント (`components/ui/`)
* **3D Rendering**: React Three Fiber (@react-three/fiber, @react-three/drei)
* **Data Fetching**: SWR
* **Testing**: Playwright (E2E, 準備中)

### Database & Infra

* **DB**: Neon (PostgreSQL)
* **Auth**: Clerk
* **Deploy**: Vercel (Frontend), Render/Cloud Run (Backend)

---

## 2. コーディング規約 (Coding Standards)

### プロジェクト共通の設計原則
* **関心事の分離 (Separation of Concerns)**: 単一のファイルや関数、コンポーネントが肥大化（ファット化）することを避けてください。常に「このコードの主な責務は何か」を考え、UI描画、ビジネスロジック、データアクセス、型定義（スキーマ）を適切なディレクトリ・ファイルに分割して実装してください。

### Backend (Python/FastAPI)

1.  **完全な型ヒントの付与 (Type Hints)**
    * すべての関数・メソッドの**引数**および**戻り値**に型ヒントを明記すること。
    * 戻り値がない場合は `-> None` を記述すること。

2. **Ruff準拠**
    * 提案するコードは Ruff のLinterおよびFormatterルールに適合していること。

3.  **`Any` 型の回避**
    * `typing.Any` の使用は原則禁止とする。
    * 型が動的に変わる場合や外部ライブラリの制約など、やむを得ない場合のみ使用し、その際は**理由をコメントで明記**すること（例: `# library X returns untyped dict`）。

4.  **Mypy エラーの解消**
    * 実装コードは `mypy` (Strict mode) のチェックをパスしなければならない。
    * `disallow_untyped_defs = true` 準拠とし、すべての関数引数と戻り値に型ヒントを記述すること。Any型は極力避け、Pydanticモデルや具体的な型を使用すること
    * Import整理: 標準ライブラリ、サードパーティ、ローカルモジュールの順序を守ること（Ruffが自動処理するが、AIも意識して出力すること）。
    * `# type: ignore` の使用は最終手段とし、使用する場合は理由を併記すること。

5.  **Pydantic / SQLModel の活用**
    * 辞書 (`dict`) をそのまま受け渡しするのではなく、可能な限り Pydantic モデルや SQLModel クラスを使用して構造化データを扱うこと。

6.  **検証**
    * コード修正後は必ずローカルで `pre-commit run --all-files` (または `mypy .`) を実行し、静的解析エラーがないことを確認してから提案すること。

7.  **関心事の分離 (Separation of Concerns)**
    * **RouterとServiceの分離**: APIルーター（`api/endpoints/`）にはリクエストのバリデーションとレスポンスの返却のみを記述し、データベース操作や複雑なビジネスロジックは必ず **Service層（`services/`）** やビジネスロジック関数に切り出すこと（ファットルーターの禁止）。
    * **スキーマ・モデルの分割**: PydanticスキーマやDBモデルが1つのファイルに肥大化（ファット化）するのを防ぐため、基本データモデルと、特定機能（例：ルール設定、外部API連携など）のスキーマは、関心事ごとに別ファイル（例: `schemas.py` と `rule_schemas.py`）に分割すること。
    * **データアクセスの分離**: 複雑なSQLAlchemy/SQLModelのクエリ操作は、再利用性を高めるためにCRUD用モジュールやリポジトリ層（`crud/` など）に分離し、ビジネスロジック内に直接ベタ書きしないこと。

### Frontend (Next.js/TypeScript)

1. **Server/Client Components**: デフォルトは Server Component。`useState` や `useEffect` が必要な場合のみ `'use client'` を付与する。
2. **SWR Usage**: データ取得は `useSWR` を使用し、`src/utils/fetcher.ts` を経由する。
3. **Type Safety**: `any` 型の使用は原則禁止。`src/types` に定義された型を使用する。
4. **Component Complexity (Logic Extraction)**:
   - データの整形、フィルタリング、複雑な状態計算ロジックはコンポーネント内に記述せず、必ず **Custom Hooks** (`useLogicName`) に切り出す。
   - コンポーネントは「描画」に専念し、ロジックを持たないようにする (View vs Logic の分離)。
   - 実装例: `BattleViewer` → `useBattleSnapshot`, `useBattleEvents` に状態計算を分離
5. **React Three Fiber (R3F) Separation**:
   - 3Dシーン (`Canvas` 内部) と 2D UI (HTML オーバーレイ) は、同じファイルに混在させず、それぞれ別のコンポーネントファイルに分割する。
   - `Canvas` を含む親コンポーネントは、レイアウトとデータの受け渡しのみを行う構成（Container Component）にする。
   - 実装例: `BattleViewer/index.tsx` (Container) → `scene/BattleScene.tsx` (3D) + `ui/BattleOverlay.tsx` (2D UI)
6. **Constants & Utils**:
   - 複数の場所で使用される定数や、3行以上の計算ロジック（色計算など）は `utils/` や `constants.ts` に移動し、純粋関数として定義する。
   - 実装例: `BattleViewer/utils.ts` - HPバー色計算、環境色取得
7. **UI Design System**:
   - UIコンポーネントは `src/components/ui/` のカスタムコンポーネントを使用する。
   - 利用可能: `Button`, `Panel`, `Heading`, `Select`, `Input` 等
   - 統一感のあるモダンSaaS風フラットデザインを維持する。

### Database (Neon/PostgreSQL)

1. **Alembic Migrations**:
   - スキーマ変更は必ず `alembic` を使用してマイグレーションファイルを生成・適用する。
   - マイグレーションファイルを生成したら、必ず `alembic upgrade head --sql` を自分で実行し、意図しない破壊的変更が含まれていないか確認してからプッシュする。
2. **SQLModel ORM**: データアクセスには SQLModel を使用し、型安全性を確保する。

#### マイグレーション作成時の注意事項

複数ブランチで並行してマイグレーションを作成すると、**複数のheadリビジョン**が発生し、`alembic upgrade head` がエラーになります。

**コンフリクト回避のベストプラクティス:**

1. **マイグレーション作成前に履歴を確認する**
   ```bash
   cd backend
   alembic heads  # 複数のheadがないか確認（1つであるべき）
   alembic history  # マイグレーション履歴と依存関係を確認
   ```

2. **mainブランチを最新化してから作業する**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature
   cd backend
   alembic upgrade head  # 最新の状態に更新
   ```

3. **複数headが発生した場合の解決方法**
   ```bash
   # 現在のheadを確認
   alembic heads
   
   # 2つのheadをマージするマイグレーションを作成
   alembic merge -m "merge_heads" <revision1> <revision2>
   
   # マージマイグレーションを適用
   alembic upgrade head
   ```

4. **Dry Run（マイグレーションの事前確認）**
   ```bash
   # 実行されるSQLを確認（実際には適用されない）
   alembic upgrade head --sql
   
   # 特定のリビジョンまでのSQLを確認
   alembic upgrade <revision_id> --sql
   
   # 現在のDBバージョンを確認
   alembic current
   
   # 次に実行されるマイグレーションを確認
   alembic show head
   ```

5. **PostgreSQL Enum型を含むマイグレーションの書き方**

   `sa.Enum(create_type=False)` を `op.create_table` の Column に渡しても、SQLAlchemyの内部イベントが Enum を再 CREATE しようとするため `DuplicateObject` エラーが発生する。
   **必ず以下のパターンで記述すること:**

   ```python
   # NG: sa.Enum を直接 Column に渡す（内部でCREATE TYPE が二重発行される）
   sa.Column('skill_rank', sa.Enum('rank_a', ..., name='skillrankenum'), nullable=False)

   # OK: DDL を明示的に発行し、Column には create_type=False の postgresql.ENUM を使う
   from sqlalchemy.dialects import postgresql

   # upgrade() 冒頭で Enum 型を作成
   op.execute(sa.text("CREATE TYPE skillrankenum AS ENUM ('rank_a', 'rank_b', 'rank_c', 'rank_d')"))

   # op.create_table 内では create_type=False を指定
   sa.Column('skill_rank', postgresql.ENUM(name='skillrankenum', create_type=False), nullable=False)

   # downgrade() では明示的に DROP
   op.execute(sa.text("DROP TYPE skillrankenum"))
   ```

6. **空マイグレーションを誤って適用してしまった場合の復旧**

   `pass` のみの空マイグレーションで `alembic upgrade head` を実行すると、DBの `alembic_version` テーブルにリビジョンが記録されるが、テーブルやEnum型は存在しない中途半端な状態になる。

   ```bash
   # 1. alembic_version を空（base）にリセット
   alembic stamp base

   # 2. マイグレーションファイルを正しい内容に修正した後、再適用
   alembic upgrade head
   ```

   なお上記の復旧手順は **DBにテーブルがまだ存在しない初期状態**に限り有効。
   既存データがある場合は手動でのDB修正が必要になるため、空ファイルでの `upgrade head` は厳禁とする。

---

## 5. テスト方針 (Testing Strategy)

### Backend: Unit Testing

**「ロジックの正確性」と「外部依存の分離」を重視する。**

* **Tool**: `pytest`
* **Location**: `backend/tests/unit/`
* **Rules**:
* DB接続や外部APIは **必ずMock化 (`unittest.mock`)** する。
* 正常系だけでなく、異常系（APIエラー等）のテストケースも網羅する。



### Frontend: E2E Testing

**「ユーザー体験（UX）の担保」を重視する。**

* **Tool**: `Playwright`
* **Location**: `frontend/e2e/`
* **Rules**:
* 実際のブラウザ操作をシミュレーションする（ログイン → 操作 → 確認）。
* テスト用アカウント（環境変数 `TEST_EMAIL` 等）を使用する。
* APIのレスポンス待ちには `page.waitForResponse` 等を使用し、 `setTimeout` のような固定待機は避ける。



---

## 6. 開発フロー (Development Process)

AI AgentがIssueに取り組む際は、以下の手順を遵守してください。

1. **Design**: `app/models` (Backend) や `src/types` (Frontend) の定義から始める。データ構造を先に確定させる。
2. **Backend Impl**: `Service` クラスの実装 → `Router` の実装 → `Unit Test` の作成・パス。
3. **Frontend Impl**: `Service` (API Client) の実装 → UIコンポーネントの実装 → ページへの組み込み。
4. **Integration**: `E2E Test` を実行し、一連のフローが動作することを確認する（現在準備中）。
5. **Report**: `docs/reports` ディレクトリに `*_REPORT` または `*_SUMMARY` などのプレフィックス付きMarkdownファイルを作成し、実装内容、テスト結果、使用方法を記載する。

---

##　7.　主要ドキュメント

開発時に参照すべき主要ドキュメント：

* `Agent.md` - AI Agent向けのコーディング規約と開発フロー
* `docs/ARCHITECTURE.md` - システム全体のディレクトリ構成・技術スタック（フロントエンド/バックエンド/インフラの役割分担）を定義
* `docs/DATABASE.md` - DBの設計方針（マルチテナント設計、UUID採用、人間の判断のオーバーライド等）と主要テーブルの役割を定義
* `docs/SPECS.md` - アプリの目的・対応日の定義・対応者の属性・シフト作成ルール（必須/推奨/優先度調整）を定義 

---


## 8. Pull Request作成時の注意

PRを作成する際は、以下を必ず含めてください：

1. **変更内容の要約** - 何を実装したか
2. **関連Issue** - `Closes #123` 形式でリンク
3. **テスト結果** - 実行したテストとその結果
4. **スクリーンショット** - UI変更の場合は必須
5. **ドキュメント更新** - 必要に応じてREADMEやdocs/を更新

**PR説明文は日本語で記述すること。**（`.github/copilot-instructions.md`に規定）

---

## 9. セキュリティと個人情報（PII）の取り扱いガイドライン

本システム（ShiftAssist）はマルチテナントSaaSであり、`worker`（従業員）の氏名などの個人情報（PII）を取り扱います。コードを生成・提案する際は、以下のセキュリティおよびプライバシー保護のルールを厳守してください。

### 1. テナント分離の徹底（最重要）
- データベースからデータを取得・更新・削除する際は、必ず `tenant_id` を用いてクエリの絞り込み（`WHERE tenant_id = ?`）を行ってください。他テナントのデータへのアクセスは重大なインシデントに直ちにつながります。
- FastAPIのルーター・エンドポイントを実装する際は、リクエスト元のテナント権限（Clerk由来の認証情報）と操作対象データのテナントが一致するかを検証する Dependency を必ず組み込んでください。

### 2. PIIのログ出力禁止とマスキング
- `worker.name` などの個人情報を、アクセスログ、エラーログ、Sentry等の監視ツールに平文で絶対に出力しないでください。
- デバッグ目的の `print()` (Python) や `console.log()` (TypeScript) の提案時にも、PIIを含まないように注意してください。

### 3. PydanticモデルによるAPIレスポンスの最小化
- DBモデルのレコードをそのままフロントエンドに返すのではなく、必ず用途に応じた Pydantic レスポンススキーマを定義してください。
- 画面表示に氏名が不要なAPI（例: シフトの統計・集計機能など）では、氏名フィールドを省いた専用のスキーマを使用し、ペイロードを最小化してください。

### 4. フロントエンドでのセキュアな状態管理
- `worker.name` などの機密データを、`localStorage` や `sessionStorage` に平文で永続化するコードを提案しないでください。
- Clerkを用いたログアウト処理やセッション切れの処理を実装する際は、SWR等のキャッシュやグローバルステートに残存しているPIIデータを確実にクリア（パージ）するようにしてください。
