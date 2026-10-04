import { NextResponse, type NextRequest } from "next/server";
import { engine } from "@/lib/engine";
import { OTP_COOKIE, forbidden, sameOrigin, setSession } from "@/lib/http";
import { addRecord, newToken, startSession, store } from "@/lib/store";

const MAX_TRIES = 3;

// Demo phone: shows the code that would have been sent by SMS for this pending sign-in.
export async function GET(request: NextRequest) {
  const pending = store.pendingOtps.get(request.cookies.get(OTP_COOKIE)?.value ?? "");
  if (!pending) return NextResponse.json({ error: "No code pending." }, { status: 404 });
  return NextResponse.json({ username: pending.username, code: pending.code });
}

export async function POST(request: NextRequest) {
  if (!sameOrigin(request)) return forbidden();
  const pendingId = request.cookies.get(OTP_COOKIE)?.value ?? "";
  const pending = store.pendingOtps.get(pendingId);
  if (!pending) {
    return NextResponse.json({ error: "Your code has expired. Please sign in again.", next: "/login" }, { status: 400 });
  }

  const body = await request.json().catch(() => ({}));
  const follow = (outcome: "otp_passed" | "otp_failed") =>
    addRecord({ ...pending.record, id: newToken(), time: new Date().toISOString(), outcome, scoringMs: null });

  try {
    if (String(body.code ?? "").trim() === pending.code) {
      store.pendingOtps.delete(pendingId);
      await engine.confirm(pending.eventId, true); // only now does this login join the user's history
      follow("otp_passed");
      const response = setSession(NextResponse.json({ next: "/account" }), startSession(pending.username));
      response.cookies.delete(OTP_COOKIE);
      return response;
    }

    pending.tries += 1;
    if (pending.tries >= MAX_TRIES) {
      store.pendingOtps.delete(pendingId);
      await engine.discard(pending.eventId);
      follow("otp_failed");
      const response = NextResponse.json({ error: "Too many wrong codes. Please try again later.", blocked: true },
                                          { status: 403 });
      response.cookies.delete(OTP_COOKIE);
      return response;
    }
    const left = MAX_TRIES - pending.tries;
    return NextResponse.json({ error: `That code isn't right. ${left} ${left === 1 ? "try" : "tries"} left.` },
                             { status: 401 });
  } catch (error) {
    console.error(error);
    return NextResponse.json({ error: "Sign-in is unavailable right now." }, { status: 503 });
  }
}
