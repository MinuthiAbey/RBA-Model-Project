import { NextResponse } from "next/server";
import { forbidden, sameOrigin, setPendingOtp, setSession } from "@/lib/http";
import { attemptSignIn } from "@/lib/login";

const WRONG_PASSWORD = "Wrong username or password.";
const BLOCKED = "We couldn't sign you in right now. Please try again later.";

export async function POST(request: Request) {
  if (!sameOrigin(request)) return forbidden();
  const body = await request.json().catch(() => ({}));
  const login = {
    username: String(body.username ?? "").trim().toLowerCase(),
    forwarded_for: request.headers.get("x-forwarded-for"),
    remote_addr: "127.0.0.1",
    user_agent: request.headers.get("user-agent"),
  };

  try {
    const attempt = await attemptSignIn(login, String(body.password ?? ""));
    switch (attempt.outcome) {
      case "wrong_password":
        return NextResponse.json({ error: WRONG_PASSWORD }, { status: 401 });
      case "allow":
        return setSession(NextResponse.json({ next: "/account" }), attempt.sessionToken);
      case "otp":
        return setPendingOtp(NextResponse.json({ next: "/verify" }), attempt.pendingId);
      case "block":
        // Never say why, so an attacker learns nothing.
        return NextResponse.json({ error: BLOCKED }, { status: 403 });
    }
  } catch (error) {
    console.error(error);
    // Fail closed: if the risk engine is unreachable, nobody signs in.
    return NextResponse.json({ error: "Sign-in is unavailable right now." }, { status: 503 });
  }
}
