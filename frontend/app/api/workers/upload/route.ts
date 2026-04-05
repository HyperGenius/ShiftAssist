/* frontend/app/api/workers/upload/route.ts */
import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function POST(request: NextRequest): Promise<NextResponse> {
  const dryRun = request.nextUrl.searchParams.get("dry_run") ?? "false";

  const upstreamUrl = `${API_BASE_URL}/api/workers/upload?dry_run=${dryRun}`;

  const forwardHeaders = new Headers();
  const authorization = request.headers.get("Authorization");
  const tenantId = request.headers.get("X-Tenant-Id");
  if (authorization) forwardHeaders.set("Authorization", authorization);
  if (tenantId) forwardHeaders.set("X-Tenant-Id", tenantId);

  const formData = await request.formData();

  const upstreamRes = await fetch(upstreamUrl, {
    method: "POST",
    headers: forwardHeaders,
    body: formData,
  });

  const data: unknown = await upstreamRes.json().catch(() => null);

  return NextResponse.json(data, { status: upstreamRes.status });
}
