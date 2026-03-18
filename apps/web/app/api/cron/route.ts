import { NextResponse } from "next/server";

export const runtime = "edge";

export async function GET(request: Request) {
  // Verify Vercel Cron secret
  const authHeader = request.headers.get("authorization");
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://beattrack-production.up.railway.app";

  try {
    const res = await fetch(`${apiUrl}/health`, { signal: AbortSignal.timeout(10_000) });
    const data = await res.json();
    return NextResponse.json({ status: "ok", backend: data });
  } catch {
    return NextResponse.json({ status: "backend_unreachable" }, { status: 502 });
  }
}
