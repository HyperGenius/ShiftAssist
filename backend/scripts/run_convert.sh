#!/bin/bash

# 開始年・月と終了年・月の設定
START_YEAR=2025
START_MONTH=6
END_YEAR=2026
END_MONTH=5

current_year=$START_YEAR
current_month=$START_MONTH

# ループ処理
while [ $current_year -lt $END_YEAR ] || { [ $current_year -eq $END_YEAR ] && [ $current_month -le $END_MONTH ]; }; do
    
    # 月を2桁（01, 02...）に整形
    formatted_month=$(printf "%02d" $current_month)
    
    # 変数の設定
    YM_UNDERSCORE="${current_year}_${formatted_month}"  # 2025_06 形式
    YM_HYPHEN="${current_year}-${formatted_month}"      # 2025-06 形式

    echo "Processing: ${YM_HYPHEN}..."

    # コマンドの実行
    python ./convert_excel_to_csv.py \
      --input ./data/${YM_UNDERSCORE}.csv \
      --output ./data/converted/${YM_UNDERSCORE}_converted.csv \
      --year-month ${YM_HYPHEN}

    # 月をインクリメント
    current_month=$((current_month + 1))
    
    # 12月を超えたら翌年の1月にリセット
    if [ $current_month -gt 12 ]; then
        current_month=1
        current_year=$((current_year + 1))
    fi
done

echo "Done!"
