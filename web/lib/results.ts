import { readFileSync } from "node:fs";
import path from "node:path";

// The landing page quotes the research results straight from the tables `make research` writes,
// so the numbers on screen can never drift from the evaluation. They live outside the code folder (config.yaml paths).
const TABLES = path.join(process.env.RESULTS_DIR ?? path.join(process.cwd(), "..", "..", "results"), "tables");

type Row = Record<string, string>;

function readTable(name: string): Row[] {
  const [header, ...lines] = readFileSync(path.join(TABLES, name), "utf8").trim().split("\n");
  const columns = header.split(",");
  return lines.map((line) => Object.fromEntries(line.split(",").map((value, i) => [columns[i], value])));
}

export type ScorerResult = { scorer: string; auc: number; stopRate: number; challengeRate: number; latencyMs: number };

export type ResultsSummary = {
  scorers: ScorerResult[];
  legitLogins: number;
  realAttacks: number;
  noHistoryShare: number;
  rforestNoHistoryStop: number;
  rforestAt10: { challengeRate: number; stopRate: number };
};

export function loadResults(): ResultsSummary | null {
  try {
    const overall = readTable("overall.csv").filter((r) => r.attack_set === "real_attack_ip");
    const latency = Object.fromEntries(readTable("latency.csv").map((r) => [r.scorer, Number(r.p50_us) / 1000]));
    const contexts = readTable("by_attack_context.csv").filter((r) => r.scorer === "rforest");
    const noHistory = contexts.find((r) => r.context === "victim_has_no_history")!;
    const at10 = readTable("operating_points.csv").find((r) => r.scorer === "rforest" && Number(r.target_legit_challenge_rate) === 0.1)!;
    return {
      scorers: overall.map((r) => ({
        scorer: r.scorer,
        auc: Number(r.roc_auc),
        stopRate: Number(r.attack_stop_rate),
        challengeRate: Number(r.legit_challenge_rate),
        latencyMs: latency[r.scorer],
      })),
      legitLogins: Number(overall[0].legit_logins),
      realAttacks: Number(overall[0].attacks),
      noHistoryShare: Number(noHistory.n) / contexts.reduce((sum, r) => sum + Number(r.n), 0),
      rforestNoHistoryStop: Number(noHistory.attack_stop_rate),
      rforestAt10: { challengeRate: Number(at10.legit_challenge_rate), stopRate: Number(at10.real_attack_ip_stop_rate) },
    };
  } catch {
    return null; // tables not generated yet (run `make research`)
  }
}
