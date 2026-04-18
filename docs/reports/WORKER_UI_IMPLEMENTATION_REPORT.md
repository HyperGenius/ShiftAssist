# Worker管理UI実装レポート

## 概要

Issue #2「Worker（対応者）管理用フロントエンドUIの実装」の対応として、`frontend/` ディレクトリにNext.js 16.2.1ベースのフロントエンドアプリケーションを新規構築しました。

## 実装内容

### 技術スタック

| 項目 | 採用技術 |
|------|----------|
| フレームワーク | Next.js 16.2.1 (App Router) |
| 言語 | TypeScript (strict mode) |
| スタイリング | Tailwind CSS v4 |
| 認証 | Clerk (`@clerk/nextjs` v7) |
| データ取得 | SWR v2 |
| フォーム | React Hook Form v7 + Zod v4 |
| Toast通知 | Sonner v2 |

### ファイル構成

```
frontend/
├── app/
│   ├── globals.css                       # グローバルスタイル（Tailwind）
│   ├── layout.tsx                        # RootLayout（ClerkProvider・Toaster統合）
│   ├── page.tsx                          # トップページ
│   ├── workers/
│   │   └── page.tsx                      # 対応者管理ページ（認証保護済み）
│   ├── sign-in/[[...sign-in]]/page.tsx   # Clerkサインインページ
│   └── sign-up/[[...sign-up]]/page.tsx   # Clerkサインアップページ
├── components/
│   ├── ui/
│   │   ├── Button.tsx                    # 汎用UIコンポーネント：ボタン
│   │   ├── Heading.tsx                   # 汎用UIコンポーネント：見出し
│   │   ├── Input.tsx                     # 汎用UIコンポーネント：テキスト入力
│   │   ├── Panel.tsx                     # 汎用UIコンポーネント：パネル
│   │   └── Select.tsx                    # 汎用UIコンポーネント：セレクトボックス
│   └── workers/
│       ├── WorkerList.tsx                # Worker一覧・CRUD操作統合コンポーネント
│       ├── WorkerForm.tsx                # 作成・編集フォーム（Zodバリデーション付き）
│       ├── WorkerModal.tsx               # 作成・編集モーダルラッパー
│       └── DeleteConfirmModal.tsx        # 削除確認モーダル
├── hooks/
│   └── useWorkers.ts                     # WorkerのCRUD操作カスタムフック（SWR使用）
├── types/
│   └── worker.ts                         # Worker TypeScript型定義
├── utils/
│   ├── apiClient.ts                      # Clerk認証トークン付与の汎用APIクライアント
│   └── fetcher.ts                        # SWR用フェッチャー関数
├── proxy.ts                              # Clerkプロキシ（認証ルート保護）
├── .env.local.example                    # 環境変数サンプル
└── package.json
```

### 主要機能の実装詳細

#### 1. Clerk認証との統合 (`proxy.ts`)
- `clerkMiddleware` + `createRouteMatcher` でルート保護を実装
- `/`、`/sign-in`、`/sign-up` はパブリックルート
- その他のページは認証必須

#### 2. 汎用APIクライアント (`utils/apiClient.ts`)
- Clerkトークンを `Authorization: Bearer <token>` ヘッダーに自動付与
- `X-Tenant-Id` ヘッダー（Clerk Organization ID）の自動付与
- GET / POST / PUT / DELETE メソッドをサポート
- エラーレスポンスのメッセージ抽出処理

#### 3. カスタムフック `useWorkers` (`hooks/useWorkers.ts`)
- SWRを使用したWorker一覧の取得（`GET /api/workers/`）
- `createWorker`, `updateWorker`, `deleteWorker` 操作のカプセル化
- ミューテーション後のキャッシュ自動更新

#### 4. WorkerList（一覧表示）
- テーブル形式でWorker一覧を表示
- スキルランク別カラーバッジ表示（A=黄、B=シアン、C=グレー、D=暗いグレー）
- 特別雇用フラグのビジュアル表示
- **ローディング状態**: スケルトンアニメーション（3行）
- **Empty State**: アイコン付きの空状態メッセージ
- エラー状態のインライン表示

#### 5. WorkerForm（作成・編集フォーム）
- React Hook Form + Zod によるバリデーション
- 氏名（必須、最大100文字）
- 所属課ID（UUID形式必須）
- スキルランク（セレクトボックス）
- 特別雇用者フラグ（チェックボックス）
- 編集時はWorkerデータで初期値セット

#### 6. DeleteConfirmModal（削除確認）
- 警告アイコン付きの確認ダイアログ
- 対象Worker名を表示
- 削除中のローディング状態表示

#### 7. モダンSaaS風UIコンポーネント
- 白/ライトグレー基調のクリーンなフラットデザイン
- シンプルなボーダー（`border-gray-200`）と控えめなシャドウ（`shadow-sm`）
- ホバー・フォーカス時はシステムカラー（`blue-600`）を使ったシンプルな表現

### 環境変数設定

`.env.local.example` を参照し、`.env.local` を作成してください。

```bash
cp frontend/.env.local.example frontend/.env.local
# Clerk DashboardからPublishable KeyとSecret Keyを取得して設定
```

## テスト結果

### ビルド結果

```
✓ Compiled successfully
✓ TypeScript type check passed
Route (app)
├ ○ /
├ ○ /_not-found
├ ƒ /sign-in/[[...sign-in]]
├ ƒ /sign-up/[[...sign-up]]
└ ƒ /workers
```

### リント結果

```
0 errors, 0 warnings
```

## 完了条件の達成状況

| 完了条件 | 状態 |
|---------|------|
| Clerkでログインしたユーザーとして、Workerの一覧が表示できること | ✅ 実装済み |
| UI上から新しいWorkerの追加、既存Workerの編集、削除が正常に行えること | ✅ 実装済み |
| バックエンドAPIへのリクエストに、Clerkの認証トークンが正しく付与されていること | ✅ 実装済み（apiClient.ts） |
| エラー時（通信失敗、バリデーションエラー）のUIフィードバックが実装されていること | ✅ 実装済み（Toast通知） |

## 今後の課題

- 所属課（Department）をDBから取得してセレクトボックスで選択できるようにする（現状はUUID直接入力）
- Playwright E2Eテストの追加
- ロール別アクセス制御（RBAC）の実装
