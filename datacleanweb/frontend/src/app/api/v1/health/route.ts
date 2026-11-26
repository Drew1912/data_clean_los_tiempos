import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
  try {
    const upstream = await fetch(new URL("/api/v1/health", backend), {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    const body = await upstream.json();
    return NextResponse.json(body, { status: upstream.status, headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ estado: "error", db: "no_disponible" }, {
      status: 503, headers: { "Cache-Control": "no-store" },
    });
  }
}
