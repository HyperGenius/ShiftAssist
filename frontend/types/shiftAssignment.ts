/** シフト要件へのワーカーアサイン情報 */
export interface WorkerAssignmentItem {
  id: string;
  worker_id: string;
  is_manual_override: boolean;
}

/** アサイン保存リクエストペイロード */
export interface ShiftAssignmentsSave {
  worker_ids: string[];
  is_manual_override: boolean;
}
