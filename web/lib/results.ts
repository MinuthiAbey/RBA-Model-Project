import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";

// The site quotes the research results straight from the tables `make research` writes,
// so the numbers on screen can never drift from the evaluation. They live outside the code folder (config.yaml paths).
export const RESULTS = process.env.RESULTS_DIR ?? path.join(process.cwd(), "..", "..", "results");
const TABLES = path.join(RESULTS, "tables");
export const FIGURES = path.join(RESULTS, "figures");

export type Row = Record<string, string>;

function readTable(name: string): Row[] {
  const [header, ...lines] = readFileSync(path.join(TABLES, name), "utf8").trim().split("\n");
  const columns = header.split(",");
  return lines.map((line) => Object.fromEntries(line.split(",").map((value, i) => [columns[i], value])));
}

export type ScorerResult = { scorer: string; auc: number; stopRate: number; challengeRate: number; latencyMs: number };

export type ResultsSummary = { scorers: ScorerResult[] };

// The headline numbers on the landing page: each model on real attacks at the 5% challenge budget.
export function loadResults(): ResultsSummary | null {
  try {
    const latency = Object.fromEntries(readTable("latency.csv").map((r) => [r.scorer, Number(r.p50_us) / 1000]));
    const scorers = readTable("overall.csv").filter((r) => r.attack_set === "real_attack_ip").map((r) => ({
      scorer: r.scorer,
      auc: Number(r.roc_auc),
      stopRate: Number(r.attack_stop_rate),
      challengeRate: Number(r.legit_challenge_rate),
      latencyMs: latency[r.scorer],
    }));
    return { scorers };
  } catch {
    return null; // tables not generated yet (run `make research`)
  }
}

export type ModelResults = Record<
  "overall" | "coldStart" | "operatingPoints" | "attackContext" | "attackerType" | "latency" | "labelledAto" |
  "splitStats" | "sampleStats" | "importance",
  Row[]
> & { figures: string[] };

const MODEL_TABLES = {
  overall: "overall.csv", coldStart: "cold_start.csv", operatingPoints: "operating_points.csv",
  attackContext: "by_attack_context.csv", attackerType: "by_attacker_type.csv", latency: "latency.csv",
  labelledAto: "labelled_ato.csv", splitStats: "split_stats.csv", sampleStats: "sample_stats.csv",
  importance: "rf_feature_importance.csv",
} as const;

// Everything the Models page shows, or null until `make research` has produced the tables.
export function loadModelResults(): ModelResults | null {
  try {
    const tables = Object.fromEntries(Object.entries(MODEL_TABLES).map(([key, file]) => [key, readTable(file)]));
    const figures = existsSync(FIGURES) ? readdirSync(FIGURES).filter((f) => f.endsWith(".png")).sort() : [];
    return { ...(tables as Omit<ModelResults, "figures">), figures };
  } catch {
    return null;
  }
}
