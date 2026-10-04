import { engine, type LoginRequest } from "./engine";
import { makeRecord } from "./http";
import { addRecord, announceOtp, newOtpCode, newToken, startSession, store } from "./store";
import type { EngineScore } from "./types";

export type Attempt =
  | { outcome: "wrong_password" }
  | { outcome: "allow"; result: EngineScore; sessionToken: string }
  | { outcome: "otp"; result: EngineScore; pendingId: string; code: string }
  | { outcome: "block"; result: EngineScore };

// One sign-in attempt: check the password, score the risk, act on the decision. Used by the sign-in page and the lab.
export async function attemptSignIn(login: LoginRequest, password: string): Promise<Attempt> {
  // Wrong passwords are never scored, but the engine still counts them for its velocity checks.
  if (!(await engine.checkPassword(login.username, password)).ok) {
    const { context } = await engine.failed(login);
    addRecord(makeRecord(login.username, "wrong_password", context));
    return { outcome: "wrong_password" };
  }

  const result = await engine.score(login);
  const record = makeRecord(login.username, result.decision, result.context, result);
  addRecord(record);

  if (result.decision === "allow") {
    await engine.confirm(result.event_id);
    return { outcome: "allow", result, sessionToken: startSession(login.username) };
  }
  if (result.decision === "otp") {
    const pendingId = newToken();
    const code = newOtpCode();
    store.pendingOtps.set(pendingId, { username: login.username, code, eventId: result.event_id, tries: 0, record });
    announceOtp({ username: login.username, code, time: new Date().toISOString() });
    console.log(`[demo OTP] ${login.username}: ${code}`);
    return { outcome: "otp", result, pendingId, code };
  }
  await engine.discard(result.event_id);
  console.log(`[ALERT] blocked sign-in for ${login.username} from ${result.context.ip}`);
  return { outcome: "block", result };
}
