import { NextResponse } from "next/server";
import { engine } from "@/lib/engine";

export const dynamic = "force-dynamic";

// Everything the sign-in lab needs: each demo user's usual sign-in, the choices on offer, and the active scorer.
export async function GET() {
  try {
    const [profiles, options, info] = await Promise.all([engine.profiles(), engine.options(), engine.info()]);
    return NextResponse.json({ profiles, options, info });
  } catch {
    return NextResponse.json({ error: "Risk engine offline" }, { status: 503 });
  }
}
