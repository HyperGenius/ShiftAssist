# backend/scripts

バックエンド運用スクリプト集。

---

## convert_excel_to_csv.py

人間閲覧用のマトリックス形式シフト表（Excel または CSV）を、ShiftAssist の
`POST /api/shift-plans/import` エンドポイントが受け付けるフラット CSV 形式に変換する。

### 前提条件

`backend/` ディレクトリで実行するか、`PYTHONPATH` に `backend/` を追加してください。

```bash
cd backend
pip install -r requirements.txt
```

### 使い方

```bash
python scripts/convert_excel_to_csv.py \
  --input  <入力ファイルパス>   \
  --output <出力CSVパス>        \
  --year-month <YYYY-MM>       \
  [--tenant-id <テナントID>]
```

| 引数 | 必須 | 説明 |
|---|---|---|
| `--input` | ✅ | 変換元の CSV または Excel（`.xlsx`/`.xls`）ファイルパス |
| `--output` | ✅ | 出力先の CSV ファイルパス |
| `--year-month` | ✅ | 対象年月（例: `2026-04`） |
| `--tenant-id` | | DB からワーカー情報を取得する際のテナント ID。省略時は環境変数 `TENANT_ID` または `TEST_ORGANIZATION_ID` を参照 |

`NEON_DATABASE_URL` 環境変数が設定されている場合は DB に接続し、ワーカー名 →
`employee_no`（職員番号）への自動マッピングを行います。未設定の場合はワーカー名をそのまま出力します。

### 入力ファイルの形式

2 行ヘッダー + データ行の構造を想定しています。

```
行 1: 日 | 曜 | 宿　　直 |  |  |  |  |  |  |  |  | 土曜当番 |  |  | 休・祝日直 |  |
行 2:    |    | 回数 | 氏名 | 交替者名 | 回数 | 氏名 | 交替者名 | ... | 回数 | 氏名 | 交替者名 | ...
行 3以降: 1 | 水 | ① | 保安１課　山田　太郎 | ... | ... | ...
```

* 1 列目: 日（1〜31）
* 2 列目: 曜日（省略可）
* 3 列目〜: カテゴリ（宿直 / 土曜当番 / 休・祝日直）のグループが繰り返す

### 出力ファイルの形式

`/api/shift-plans/import` の CSV インポート形式と互換：

```csv
date,slot_type,worker_id_1,worker_id_2,...
2026-04-01,weekday_night,1234567,2468013
2026-04-04,sat_day,9876543,
2026-04-05,sun_hol_night,1234567,2468013
```

### SlotType マッピング

| カテゴリ列 | 対象日の条件 | SlotType |
|---|---|---|
| 宿直 | 平日（非祝日） | `weekday_night` |
| 宿直 | 土曜 | `sat_night` |
| 宿直 | 日曜・祝日 | `sun_hol_night` |
| 宿直 | 長期連休（GW 等） | `long_hol_night` |
| 土曜当番 | 土曜 | `sat_day` |
| 休・祝日直 | 日曜・祝日 | `sun_hol_day` |
| 休・祝日直 | 長期連休 | `long_hol_day` |

祝日情報は DB の `tenant_holidays` テーブルを優先し、未登録の場合は
[jpholiday](https://pypi.org/project/jpholiday/) による日本標準祝日でフォールバックします。

### 実行例

```bash
# DB 接続あり（ワーカー名 → employee_no 変換）
NEON_DATABASE_URL="postgresql://user:pass@host/db" \
python scripts/convert_excel_to_csv.py \
  --input  data/shift_2026_04.csv \
  --output data/import_2026_04.csv \
  --year-month 2026-04 \
  --tenant-id org_xxxxxxxxxxxx

# DB 接続なし（ワーカー名をそのまま出力）
python scripts/convert_excel_to_csv.py \
  --input  data/shift_2026_04.xlsx \
  --output data/import_2026_04.csv \
  --year-month 2026-04
```

---

## seed.py

開発・テスト用のダミーデータを DB に投入するスクリプト。

```bash
NEON_DATABASE_URL="..." python scripts/seed.py
```

> ⚠️ 既存データを全件削除してから投入します。本番環境では使用しないでください。
