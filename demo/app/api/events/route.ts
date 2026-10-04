import { NextResponse } from "next/server";
import { engine } from "@/lib/engine";
import { store } from "@/lib/store";

export const dynamic = "force-dynamic";

// Every stored decision as JSON: the dashboard's starting point (the live stream adds to it).
export async function GET() {
  const info = await engine.info().catch(() => null);
  return NextResponse.json({ records: store.records, latestOtp: store.latestOtp, info });
}
