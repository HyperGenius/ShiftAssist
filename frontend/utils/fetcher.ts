// frontend/utils/fetcher.ts
// SWR 用汎用フェッチャー（Clerk 認証トークン付与）

import { createApiClient, type ApiClientOptions } from "@/utils/apiClient";

/**
 * SWR の fetcher として使用する関数。
 * key には [path, token, tenantId] の形式を想定する。
 */
export async function fetcher<T>([
  path,
  token,
  tenantId,
]: [string, string | null, string | null | undefined]): Promise<T> {
  const options: ApiClientOptions = { token, tenantId };
  return createApiClient(options).get<T>(path);
}
