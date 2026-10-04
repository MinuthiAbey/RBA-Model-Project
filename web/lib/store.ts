import { randomBytes, randomInt } from "node:crypto";
import type { LoginRecord, OtpNotice, StreamMessage } from "./types";

// Sessions, pending codes and the live decision feed live in memory; accounts and history are in the API's database.
type PendingOtp = { username: string; code: string; eventId: string; tries: number; record: LoginRecord };

type Store = {
  sessions: Map<string, string>;
  pendingOtps: Map<string, PendingOtp>;
  records: LoginRecord[];
  latestOtp: OtpNotice | null;
  listeners: Set<(message: StreamMessage) => void>;
};

const MAX_RECORDS = 2000;

function createStore(): Store {
  return { sessions: new Map(), pendingOtps: new Map(), records: [], latestOtp: null, listeners: new Set() };
}

// Next.js reloads modules in development; keeping the store on globalThis stops that from wiping it.
const globalForStore = globalThis as unknown as { demoStore?: Store };
export const store = (globalForStore.demoStore ??= createStore());

export function newToken(): string {
  return randomBytes(24).toString("hex");
}

export function startSession(username: string): string {
  const token = newToken();
  store.sessions.set(token, username);
  return token;
}

export function newOtpCode(): string {
  return randomInt(0, 1_000_000).toString().padStart(6, "0");
}

export function addRecord(record: LoginRecord): void {
  store.records.unshift(record);
  store.records.length = Math.min(store.records.length, MAX_RECORDS);
  broadcast({ type: "login", record });
}

export function announceOtp(notice: OtpNotice): void {
  store.latestOtp = notice;
  broadcast({ type: "otp", notice });
}

function broadcast(message: StreamMessage): void {
  for (const listener of store.listeners) listener(message);
}
