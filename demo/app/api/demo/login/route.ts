import { NextResponse } from "next/server";
import { engine, type LoginRequest } from "@/lib/engine";
import { forbidden, makeRecord, sameOrigin, setPendingOtp, setSession } from "@/lib/http";
import { attemptSignIn } from "@/lib/login";
import { addRecord } from "@/lib/store";
import type { LabResult, Simulation } from "@/lib/types";

// Sign-in lab (local demo only): signs in with a context the presenter chose, and shows what happened behind the scenes.
export async function POST(request: Request) {
  if (!sameOrigin(request)) return forbidden();
  const body = await request.json().catch(() => ({}));
  const simulate = body.simulate as Simulation;
  const login: LoginRequest = {
    username: String(body.username ?? "").trim().toLowerCase(),
    forwarded_for: null,
    remote_addr: "127.0.0.1",
    user_agent: null,
    simulate,
    scorer: String(body.scorer ?? ""),
    budget: String(body.budget ?? ""),
    compare: true,
  };
  const failures = Math.min(Math.max(Number(body.failures) || 0, 0), 10);

  try {
    // Optional wrong-password attempts first, from the same place, to show the failed-attempts signal.
    for (let i = 0; i < failures; i++) {
      const { context } = await engine.failed(login);
      addRecord(makeRecord(login.username, "wrong_password", context));
    }
    const attempt = await attemptSignIn(login, String(body.password ?? ""));
    if (attempt.outcome === "wrong_password") return NextResponse.json({ outcome: "wrong_password" } satisfies LabResult);

    const { result } = attempt;
    const payload: LabResult = {
      outcome: attempt.outcome, score: result.score, reasons: result.reasons, scoring_ms: result.scoring_ms,
      context: result.context, scorer: result.scorer, budget: result.budget, comparison: result.comparison,
      trusted_since: result.trusted_since, trust_paused: result.trust_paused,
    };
    if (attempt.outcome === "allow") return setSession(NextResponse.json(payload), attempt.sessionToken);
    if (attempt.outcome === "otp") return setPendingOtp(NextResponse.json({ ...payload, phone: attempt.code }), attempt.pendingId);
    return NextResponse.json(payload);
  } catch (error) {
    console.error(error);
    return NextResponse.json({ error: "Risk engine offline" }, { status: 503 });
  }
}
