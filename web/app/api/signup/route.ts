import { NextResponse } from "next/server";
import { engine, type LoginRequest } from "@/lib/engine";
import { forbidden, makeRecord, sameOrigin, setSession } from "@/lib/http";
import { addRecord, startSession } from "@/lib/store";
import type { Simulation } from "@/lib/types";

export async function POST(request: Request) {
  if (!sameOrigin(request)) return forbidden();
  const body = await request.json().catch(() => ({}));
  const signup: LoginRequest = {
    username: String(body.username ?? "").trim().toLowerCase(),
    forwarded_for: request.headers.get("x-forwarded-for"),
    remote_addr: "127.0.0.1",
    user_agent: request.headers.get("user-agent"),
    simulate: body.simulate as Simulation | undefined,
  };
  if (String(body.password ?? "") !== String(body.confirm ?? "")) {
    return NextResponse.json({ error: "The passwords don't match." }, { status: 400 });
  }

  try {
    const result = await engine.register(signup, String(body.password ?? ""));
    if (!result.created || !result.context) return NextResponse.json({ error: result.error }, { status: 400 });
    addRecord(makeRecord(signup.username, "signed_up", result.context));
    return setSession(NextResponse.json({ next: "/account" }), startSession(signup.username));
  } catch (error) {
    console.error(error);
    return NextResponse.json({ error: "Sign-up is unavailable right now." }, { status: 503 });
  }
}
