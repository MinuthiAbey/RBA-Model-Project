import type { EngineContext, EngineScore, LabOptions, Profile, Simulation } from "./types";

// The Python risk engine runs as a small local scoring API (`python -m api.server`).
const ENGINE_URL = process.env.ENGINE_URL ?? "http://127.0.0.1:8001";

export type LoginRequest = {
  username: string;
  forwarded_for: string | null;
  remote_addr: string;
  user_agent: string | null;
  simulate?: Simulation;
  scorer?: string; // sign-in lab only: which model and challenge budget to use
  budget?: string;
  compare?: boolean;
};

async function call<T>(path: string, body?: object): Promise<T> {
  const response = await fetch(`${ENGINE_URL}${path}`, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Risk engine returned ${response.status} for ${path}`);
  return response.json() as Promise<T>;
}

export const engine = {
  info: () => call<{ scorer: string; challenge_budget: number }>("/info"),
  profiles: () => call<Record<string, Profile>>("/profiles"),
  options: () => call<LabOptions>("/options"),
  checkPassword: (username: string, password: string) => call<{ ok: boolean }>("/accounts/check", { username, password }),
  register: (request: LoginRequest, password: string) =>
    call<{ created: boolean; error?: string; context?: EngineContext }>("/accounts/register", { ...request, password }),
  score: (request: LoginRequest) => call<EngineScore>("/score", request),
  failed: (request: LoginRequest) => call<{ context: EngineContext }>("/failed", request),
  // verified = the user passed a one-time code, which also lets the engine remember this place and device.
  confirm: (eventId: string, verified = false) => call<{ confirmed: boolean }>("/confirm", { event_id: eventId, verified }),
  discard: (eventId: string) => call<{ discarded: boolean }>("/discard", { event_id: eventId }),
};
