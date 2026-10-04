import { randomBytes, randomInt, scryptSync, timingSafeEqual } from "node:crypto";
import type { LoginRecord, OtpNotice, StreamMessage } from "./types";

// Everything lives in memory and is seeded on start-up, so every demo run begins from the same state.
type PendingOtp = { username: string; code: string; eventId: string; tries: number; record: LoginRecord };

type Store = {
  passwords: Map<string, { salt: string; hash: string }>;
  sessions: Map<string, string>;
  pendingOtps: Map<string, PendingOtp>;
  records: LoginRecord[];
  latestOtp: OtpNotice | null;
  listeners: Set<(message: StreamMessage) => void>;
};

const DEMO_PASSWORD = "demo1234";
const DEMO_USERS = ["alice", "bob", "charlie"];
const MAX_RECORDS = 2000;

function hashPassword(password: string, salt: string): string {
  return scryptSync(password, salt, 32).toString("hex");
}

function createStore(): Store {
  const passwords = new Map<string, { salt: string; hash: string }>();
  for (const user of DEMO_USERS) {
    const salt = randomBytes(16).toString("hex");
    passwords.set(user, { salt, hash: hashPassword(DEMO_PASSWORD, salt) });
  }
  return { passwords, sessions: new Map(), pendingOtps: new Map(), records: [], latestOtp: null, listeners: new Set() };
}

// Next.js reloads modules in development; keeping the store on globalThis stops that from wiping it.
const globalForStore = globalThis as unknown as { demoStore?: Store };
export const store = (globalForStore.demoStore ??= createStore());

export function checkPassword(username: string, password: string): boolean {
  const saved = store.passwords.get(username);
  if (!saved) return false;
  return timingSafeEqual(Buffer.from(hashPassword(password, saved.salt), "hex"), Buffer.from(saved.hash, "hex"));
}

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
