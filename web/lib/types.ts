export type Decision = "allow" | "otp" | "block";

// Everything the dashboard shows for one sign-in attempt.
export type LoginRecord = {
  id: string;
  time: string;
  username: string;
  outcome: Decision | "wrong_password" | "otp_passed" | "otp_failed" | "signed_up";
  score: number | null;
  explanation: string;
  scoringMs: number | null;
  ip: string;
  country: string | null;
  device: string;
  priorLogins: number;
};

export type OtpNotice = { username: string; code: string; time: string };

export type StreamMessage =
  | { type: "login"; record: LoginRecord }
  | { type: "otp"; notice: OtpNotice };

export type EngineContext = {
  ip: string;
  country: string | null;
  asn: number | null;
  browser: string;
  os: string;
  device_type: string;
  prior_logins: number;
  time: string;
};

export type Reason = { code: string; text: string; weight: number };

export type Comparison = { scorer: string; score: number; decision: Decision; trusted: boolean; reason: string | null };

export type EngineScore = {
  event_id: string;
  scorer: string;
  budget: string;
  comparison: Comparison[] | null;
  trusted_since: string | null;
  trust_paused: string | null;
  decision: Decision;
  score: number;
  reasons: Reason[];
  explanation: string;
  scoring_ms: number;
  context: EngineContext;
};

// Sign-in lab: the context the presenter chooses instead of the real request's.
export type Simulation = { country: string; asn: number; ip: "usual" | "new"; device: string; hour: number };

export type Profile = {
  logins: number;
  last_login: string | null;
  usual: null | {
    country: string; asn: number; ip: string; device: string | null;
    browser: string; os: string; device_type: string; hour: number | null;
  };
  seen_countries: string[];
  seen_devices: string[];
  trusted: { country: string; asn: number; device: string | null; since: string }[];
};

export type LabOptions = {
  locations: { country: string; name: string; asns: number[] }[];
  devices: { key: string; label: string; device_type: string }[];
  scorers: string[];
  budgets: string[];
};

export type LabResult = {
  outcome: "wrong_password" | Decision;
  score?: number;
  reasons?: Reason[];
  scoring_ms?: number;
  context?: EngineContext;
  scorer?: string;
  budget?: string;
  comparison?: Comparison[] | null;
  trusted_since?: string | null;
  trust_paused?: string | null;
  phone?: string; // the one-time code, as the demo phone would receive it
};
