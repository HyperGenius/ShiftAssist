# Alembic マイグレーション手順

`env.py` を使って Neon 上の PostgreSQL にテーブルを作成・更新する手順です。

## 概要

`env.py` は起動時に以下を行います。

1. `backend/.env` を読み込み、`NEON_DATABASE_URL` を取得する
2. `app/models/models.py` のモデル定義を読み込む
3. Neon に接続してマイグレーションを実行する

> **注意:** `env.py` 内の `sys.path.append(os.getcwd())` により、すべての alembic コマンドは **`backend/` ディレクトリから実行**する必要があります。

---

## 前提条件

| 条件 | 確認方法 |
|---|---|
| Neon DB が作成済み | `infra/neon/` の Terraform 手順を完了していること |
| `backend/.env` に接続文字列が設定済み | `NEON_DATABASE_URL=postgresql://...` の行が存在すること |
| Python 仮想環境が有効 | `source venv/bin/activate`（`backend/` で実行）|
| 依存パッケージがインストール済み | `pip install -r requirements.txt` |

---

## 手順

### 1. `backend/.env` の確認

`infra/neon/` で Terraform を適用済みであれば、以下のコマンドで接続文字列を `.env` に書き出せます。

```bash
# infra/neon/ ディレクトリで実行
terraform output -raw database_url >> ../../backend/.env
```

`backend/.env` に以下の行が含まれていることを確認してください。

```env
NEON_DATABASE_URL=postgresql://shift_assist_owner:<password>@<host>/shift_assist_db?sslmode=require
```

### 2. 仮想環境の有効化・依存関係のインストール

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### 3. `alembic.ini` の作成（初回のみ）

`backend/` に `alembic.ini` がない場合は、手動で作成してください。  
`alembic init` を使う場合は、カスタマイズ済みの `alembic/env.py` が**上書きされないよう**以下の手順で行います。

```bash
# backend/ ディレクトリで実行
alembic init alembic_tmp          # 一時ディレクトリに出力
cp alembic_tmp/alembic.ini .      # alembic.ini だけコピー
rm -rf alembic_tmp                # 一時ディレクトリを削除
```

または、以下の内容で `backend/alembic.ini` を直接作成してください。

```ini
[alembic]
script_location = alembic
file_template = %%(year)d%%(month).2d%%(day).2d_%%(rev)s_%%(slug)s
prepend_sys_path = .

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### 4. `alembic/versions/` ディレクトリの作成（初回のみ）

```bash
mkdir -p alembic/versions
```

### 5. マイグレーションファイルの自動生成

モデル定義（`app/models/models.py`）からマイグレーションを自動生成します。

```bash
# backend/ ディレクトリで実行
alembic revision --autogenerate -m "initial schema"
```

`alembic/versions/` 配下にファイルが生成されます。内容を確認してから次のステップに進んでください。

### 6. Neon に適用

```bash
alembic upgrade head
```

成功すると、Neon 上の `shift_assist_db` に全テーブルが作成されます。

---

## よく使うコマンド

| コマンド | 説明 |
|---|---|
| `alembic upgrade head` | 最新マイグレーションを適用 |
| `alembic downgrade -1` | 1つ前のバージョンに戻す |
| `alembic current` | 現在適用されているリビジョンを確認 |
| `alembic history` | マイグレーション履歴を表示 |
| `alembic revision --autogenerate -m "<message>"` | モデル変更からマイグレーションを自動生成 |
