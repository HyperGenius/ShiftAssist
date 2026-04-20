/**
 * 文字列比較のための正規化ユーティリティ
 *
 * 全角→半角変換（NFKC正規化）と大文字→小文字変換を行い、
 * 大文字小文字・全半角を問わない部分一致検索を可能にする。
 */

/**
 * 文字列を検索用に正規化する。
 * - NFKC正規化で全角英数字・カナを半角に変換
 * - 小文字に統一
 */
export function normalizeForSearch(str: string): string {
  return str.normalize("NFKC").toLowerCase();
}

/**
 * `text` が `query` を部分一致で含むかを、正規化して比較する。
 * query が空文字の場合は常に true を返す。
 */
export function matchesNormalized(text: string, query: string): boolean {
  if (query === "") return true;
  return normalizeForSearch(text).includes(normalizeForSearch(query));
}
