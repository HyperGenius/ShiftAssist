// frontend/utils/apiClient.ts
// Clerk 認証トークンをヘッダーに付与する汎用 API クライアント

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type ApiClientOptions = {
  token: string | null;
  tenantId: string | null | undefined;
};

async function request<T>(
  path: string,
  options: ApiClientOptions,
  init?: RequestInit,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (options.token) {
    headers["Authorization"] = `Bearer ${options.token}`;
  }

  if (options.tenantId) {
    headers["X-Tenant-Id"] = options.tenantId;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...headers,
      ...(init?.headers as Record<string, string> | undefined),
    },
  });

  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        message = body.detail;
      }
    } catch {
      // ignore JSON parse error
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function createApiClient(options: ApiClientOptions) {
  return {
    get: <T>(path: string) =>
      request<T>(path, options, { method: "GET" }),
    post: <T>(path: string, body: unknown) =>
      request<T>(path, options, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    put: <T>(path: string, body: unknown) =>
      request<T>(path, options, {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    delete: <T>(path: string) =>
      request<T>(path, options, { method: "DELETE" }),
  };
}
