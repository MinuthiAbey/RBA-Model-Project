import { NextResponse } from "next/server";
import { newToken } from "./store";
import type { EngineContext, LoginRecord } from "./types";

export const SESSION_COOKIE = "session";
export const OTP_COOKIE = "otp_pending";

// The demo runs on plain http://127.0.0.1; set COOKIE_SECURE=true when serving over HTTPS.
export const cookieOptions = { httpOnly: true, sameSite: "strict" as const, path: "/", secure: process.env.COOKIE_SECURE === "true" };

// Basic CSRF guard: state-changing requests must come from this site.
export function sameOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  return origin === null || new URL(origin).host === request.headers.get("host");
}

export function forbidden(): NextResponse {
  return NextResponse.json({ error: "Request rejected." }, { status: 403 });
}

export function deviceLabel(context: EngineContext): string {
  return `${context.device_type} · ${context.browser} · ${context.os}`;
}

export function makeRecord(username: string, outcome: LoginRecord["outcome"], context: EngineContext,
                           score: { score: number; explanation: string; scoring_ms: number } | null = null): LoginRecord {
  return {
    id: newToken(),
    time: new Date().toISOString(),
    username,
    outcome,
    score: score?.score ?? null,
    explanation: score?.explanation ?? (outcome === "wrong_password" ? "Wrong password (not scored)" : ""),
    scoringMs: score?.scoring_ms ?? null,
    ip: context.ip,
    country: context.country,
    device: deviceLabel(context),
    priorLogins: context.prior_logins,
  };
}

export function setSession(response: NextResponse, token: string): NextResponse {
  response.cookies.set(SESSION_COOKIE, token, { ...cookieOptions, maxAge: 60 * 60 });
  return response;
}

export function setPendingOtp(response: NextResponse, pendingId: string): NextResponse {
  response.cookies.set(OTP_COOKIE, pendingId, { ...cookieOptions, maxAge: 5 * 60 });
  return response;
}
