import { NextResponse, type NextRequest } from "next/server";
import { SESSION_COOKIE, forbidden, sameOrigin } from "@/lib/http";
import { store } from "@/lib/store";

export async function POST(request: NextRequest) {
  if (!sameOrigin(request)) return forbidden();
  store.sessions.delete(request.cookies.get(SESSION_COOKIE)?.value ?? "");
  const response = NextResponse.json({ next: "/" });
  response.cookies.delete(SESSION_COOKIE);
  return response;
}
