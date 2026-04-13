// frontend/utils/labels.ts
// シフト関連のラベル共通定数

import type { SlotType } from "@/types/shiftRequirement";

/**
 * SlotType の日本語フルラベルマッピング
 * シフト作成画面・雇用形態ルール設定画面など複数箇所で共通利用する
 */
export const SLOT_TYPE_FULL_LABELS: Record<SlotType, string> = {
  weekday_night: "平日夜間",
  sat_day: "土曜昼間",
  sat_night: "土曜夜間",
  sun_hol_day: "日曜・祝日昼間",
  sun_hol_night: "日曜・祝日夜間",
  long_hol_day: "長期連休昼間",
  long_hol_night: "長期連休夜間",
  sat_pre_hol_night: "土曜・祝前日夜間",
};

/**
 * SlotType の全選択肢（value と日本語ラベルのペア）
 * チェックボックス・セレクトボックス等の一覧表示に使用
 */
export const SLOT_TYPE_OPTIONS: { value: SlotType; label: string }[] = (
  Object.entries(SLOT_TYPE_FULL_LABELS) as [SlotType, string][]
).map(([value, label]) => ({ value, label }));
