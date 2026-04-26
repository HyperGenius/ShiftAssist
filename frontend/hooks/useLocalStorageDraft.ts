"use client";

import { useCallback, useEffect, useRef } from "react";
import type { CalendarState } from "@/types/shiftRequirement";

const DEBOUNCE_MS = 1000;
// localStorage の容量上限の目安（5MB）
const MAX_STORAGE_BYTES = 5 * 1024 * 1024;

export interface LocalStorageDraft {
  calendarState: CalendarState;
  savedAt: string; // ISO 8601
}

/** localStorage のキーを生成する */
export function buildDraftKey(
  tenantId: string,
  departmentId: string,
  yearMonth: string,
): string {
  return `shift-draft:${tenantId}:${departmentId}:${yearMonth}`;
}

interface UseLocalStorageDraftOptions {
  tenantId: string | null;
  departmentId: string;
  yearMonth: string; // YYYY-MM
  calendarState: CalendarState;
  readOnly?: boolean;
}

interface UseLocalStorageDraftResult {
  /** localStorage から下書きを読み込む */
  loadDraft: () => LocalStorageDraft | null;
  /** localStorage の下書きを削除する */
  clearDraft: () => void;
  /** localStorage の保存タイムスタンプを取得する */
  getDraftTimestamp: () => string | null;
}

/**
 * calendarState を debounce して localStorage に保存するカスタムフック。
 * readOnly モード時は保存を行わない。
 */
export function useLocalStorageDraft({
  tenantId,
  departmentId,
  yearMonth,
  calendarState,
  readOnly = false,
}: UseLocalStorageDraftOptions): UseLocalStorageDraftResult {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const getKey = useCallback((): string | null => {
    if (!tenantId) return null;
    return buildDraftKey(tenantId, departmentId, yearMonth);
  }, [tenantId, departmentId, yearMonth]);

  // calendarState 変化時に debounce して保存
  useEffect(() => {
    if (readOnly) return;
    if (!tenantId) return;

    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
    }

    timerRef.current = setTimeout(() => {
      const key = getKey();
      if (!key) return;

      const draft: LocalStorageDraft = {
        calendarState,
        savedAt: new Date().toISOString(),
      };

      try {
        const serialized = JSON.stringify(draft);
        // 容量チェック（概算）
        if (serialized.length > MAX_STORAGE_BYTES) {
          console.warn(
            "[useLocalStorageDraft] 下書きデータが大きすぎるため localStorage への保存を省略しました。",
            { byteSize: serialized.length },
          );
          return;
        }
        localStorage.setItem(key, serialized);
      } catch (e) {
        console.warn("[useLocalStorageDraft] localStorage への保存に失敗しました。", e);
      }
    }, DEBOUNCE_MS);

    return () => {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
      }
    };
  }, [calendarState, readOnly, tenantId, getKey]);

  const loadDraft = useCallback((): LocalStorageDraft | null => {
    const key = getKey();
    if (!key) return null;
    try {
      const raw = localStorage.getItem(key);
      if (!raw) return null;
      return JSON.parse(raw) as LocalStorageDraft;
    } catch {
      return null;
    }
  }, [getKey]);

  const clearDraft = useCallback((): void => {
    const key = getKey();
    if (!key) return;
    localStorage.removeItem(key);
  }, [getKey]);

  const getDraftTimestamp = useCallback((): string | null => {
    const draft = loadDraft();
    return draft?.savedAt ?? null;
  }, [loadDraft]);

  return { loadDraft, clearDraft, getDraftTimestamp };
}
