# FlexShift 🗓️

FlexShift（フレックスシフト）は、複雑な業務ルールが絡む「夜勤・休日対応シフト」の作成を支援するための、人間中心型シフト管理SaaSです。

## 💡 Why FlexShift?
シフト作成において、すべての条件を完璧に満たす自動生成アルゴリズムを組むことは困難であり、また現場の細かな事情（急な予定変更、人間関係、当人同士の合意によるシフト交換など）に柔軟に対応できません。
本システムは**完全自動化を目指すのではなく、人間の作成作業を強力に支援・検証するツール**として設計されています。

フロントエンドでのリアルタイムなルール検証（アドホック計算）と、バックエンドでの厳密なデータ整合性チェックを組み合わせることで、ストレスのないシフト作成体験を提供します。

## ✨ 主な機能と特徴
* **直感的なUI**: Next.jsによるリッチなフロントエンド。ドラッグ＆ドロップで直感的にシフトの割り当て・入れ替えが可能。
* **リアルタイムなルール検証**: アサインした瞬間に「勤務間隔（中9日空き）」「スキルランク要件」「所属課の重複」などをフロントエンドで即座に判定し、警告やエラーをUIにフィードバック。
* **人間の判断を尊重するオーバーライド**: ルール違反（警告）があっても、運用上の合意があれば手動で確定（強制保存）できる柔軟なデータ構造。
* **SaaS対応（マルチテナント）**: ClerkのOrganizations機能とPostgreSQLの論理分離（`tenant_id`）を利用し、初期段階から複数組織での利用を想定した堅牢なアーキテクチャ。
* **柔軟なルールエンジン**: テナントごとに異なるシフト作成ルールをJSONスキーマで管理。

## 🛠️ 技術スタック
フルスタックWebアプリケーションとして、以下のモダンな技術を採用しています。

* **Frontend**: Next.js / TypeScript / Tailwind CSS / 状態管理（TBD）
* **Backend**: Python / FastAPI / Pydantic / SQLAlchemy / Alembic
* **Database**: Neon (Serverless PostgreSQL)
* **Auth**: Clerk (B2B SaaS向けマルチテナント認証)
* **Infrastructure**: Vercel (Frontend) / Google Cloud Run (Backend) / Terraform

## 📁 ディレクトリ構成
本リポジトリはモノレポ構成を採用しています。

```text
.
├── frontend/   # フロントエンド (UI / 状態管理 / リアルタイム検証)
├── backend/    # バックエンド (API提供 / 最終バリデーション / DB操作)
├── infra/      # インフラストラクチャコード (Terraform)
└── docs/       # 各種ドキュメント
````

## 📚 ドキュメント

システムの詳細な仕様や設計については、`docs/` ディレクトリを参照してください。

  * [`docs/SPECS.md`](https://www.google.com/search?q=./docs/SPECS.md) - プロジェクトの目的、シフトの対象枠、対応者属性、シフト作成ルールの詳細
  * [`docs/ARCHITECTURE.md`](https://www.google.com/search?q=./docs/ARCHITECTURE.md) - システムアーキテクチャ、フロントエンドとバックエンドの役割分担
  * [`docs/DATABASE.md`](https://www.google.com/search?q=./docs/DATABASE.md) - データベース設計方針と主要テーブルの定義

## 🚀 開発の始め方 (Getting Started)

*(※ 今後、ローカル環境の構築手順などをここに追記します)*
