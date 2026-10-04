# Evaluates every scorer on the test period: replay in time order, score each login, then let history learn.

import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.config import load_config  # noqa: E402
from engine.decision import Threshold, thresholds_from_dict, threshold_for_rate  # noqa: E402
from engine.features import FEATURES, extract  # noqa: E402
from engine.history import InMemoryHistory  # noqa: E402
from engine.scorers.base import Scorer  # noqa: E402
from engine.scorers.rules import RULES, RuleScorer  # noqa: E402
from research.common import MODELS, PROCESSED, SCORERS, TABLES, classify, load_period, replay, save_table  # noqa: E402

LATENCY_SAMPLE = 2000
# Each real or simulated attack population is compared against the same legitimate logins.
ATTACK_SETS = {
    "real_attack_ip": lambda t: t["kind"] == "attack_ip",
    "real_attack_ip_password_correct": lambda t: (t["kind"] == "attack_ip") & t["success"],
    "simulated": lambda t: t["kind"] == "simulated",
}


def bucket_labels(prior_logins: np.ndarray, buckets: list) -> np.ndarray:
    labels = np.empty(len(prior_logins), dtype=object)
    for low, high in buckets:
        top = np.inf if high is None else high
        label = f"{low}+" if high is None else (str(low) if low == high else f"{low}-{high}")
        labels[(prior_logins >= low) & (prior_logins <= top)] = label
    return labels


def wilson(successes: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return np.nan, np.nan
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def equal_error_rate(labels: np.ndarray, scores: np.ndarray) -> float:
    fpr, tpr, _ = roc_curve(labels, scores)
    i = np.argmin(np.abs(fpr - (1 - tpr)))
    return float((fpr[i] + 1 - tpr[i]) / 2)


def attack_context(event, user) -> str:
    # How closely a real attack matched the victim's usual country and device at that moment.
    if user.login_count == 0:
        return "victim_has_no_history"
    if user.seen["country"][event.country] == 0:
        return "new_country"
    known_device = all(user.seen[f][getattr(event, f)] > 0 for f in ("browser", "os", "device_type"))
    return "home_country_known_device" if known_device else "home_country_new_device"


def score_test_period(scorers: dict, history: InMemoryHistory, logins: pd.DataFrame, seed: int):
    kinds = classify(logins)
    scored = np.isin(kinds, ["legit", "attack_ip", "simulated"])
    rng = np.random.default_rng(seed)
    timed = set(rng.choice(np.flatnonzero(scored), size=min(LATENCY_SAMPLE, scored.sum()), replace=False))
    rows, latency = [], []

    def on_event(i: int, event) -> None:
        user = history.get_user(event.user_id)
        features = extract(event, history)
        features["freeman_raw"] = scorers["freeman"].raw_score(event, history)[0]
        features["context"] = attack_context(event, user) if kinds[i] != "legit" else ""
        features["row"] = i
        rows.append(features)
        if i in timed:
            # End-to-end time for one login: features, score, reasons and calibration.
            for name, scorer in scorers.items():
                start = time.perf_counter_ns()
                scorer.score(event, history)
                latency.append((name, (time.perf_counter_ns() - start) / 1000))

    replay(logins, history, on_event, scored)
    table = pd.DataFrame(rows)
    picked = logins.iloc[table.pop("row").to_numpy()]
    table["kind"] = kinds[scored]
    for column in ["row_id", "user_id", "timestamp", "success", "attacker_type", "target_bucket"]:
        table[column] = picked[column].to_numpy()
    return table, pd.DataFrame(latency, columns=["scorer", "microseconds"])


def add_scores(table: pd.DataFrame, scorers: dict, thresholds: dict) -> None:
    # Challenge/block columns are probabilities: 1 or 0, except for logins tied exactly at a threshold.
    for name, scorer in scorers.items():
        raw = table["freeman_raw"].to_numpy() if name == "freeman" else scorer.raw_scores(table)
        t = thresholds_from_dict(thresholds[name])
        table[f"{name}_raw"] = raw
        table[f"{name}_score"] = scorer.calibrator.scores(raw)
        table[f"{name}_challenge"] = t.otp.expected_flags(raw)
        table[f"{name}_block"] = t.block.expected_flags(raw)


def rate_row(stopped: np.ndarray) -> dict:
    low, high = wilson(float(stopped.sum()), len(stopped))
    return {"n": len(stopped), "rate": stopped.mean() if len(stopped) else np.nan, "ci_low": low, "ci_high": high}


def overall_table(table: pd.DataFrame) -> pd.DataFrame:
    legit = table["kind"] == "legit"
    rows = []
    for name in SCORERS:
        raw, challenged, blocked = table[f"{name}_raw"], table[f"{name}_challenge"], table[f"{name}_block"]
        for attack_set, pick in ATTACK_SETS.items():
            attack = pick(table)
            both = legit | attack
            labels, flagged = attack[both].to_numpy(int), challenged[both].to_numpy()
            caught = flagged[labels == 1].sum()
            precision = caught / flagged.sum() if flagged.sum() else 0.0
            recall = caught / labels.sum()
            rows.append({
                "scorer": name, "attack_set": attack_set,
                "attacks": int(attack.sum()), "legit_logins": int(legit.sum()),
                "attack_stop_rate": challenged[attack].mean(),
                "attack_block_rate": blocked[attack].mean(),
                "legit_challenge_rate": challenged[legit].mean(),
                "legit_block_rate": blocked[legit].mean(),
                "roc_auc": roc_auc_score(labels, raw[both]),
                "equal_error_rate": equal_error_rate(labels, raw[both].to_numpy()),
                "precision": precision, "recall": recall,
                "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            })
    return pd.DataFrame(rows)


def cold_start_table(table: pd.DataFrame, bucket_order: list[str]) -> pd.DataFrame:
    populations = {"legit": table["kind"] == "legit", "real_attack_ip": table["kind"] == "attack_ip",
                   "simulated": table["kind"] == "simulated"}
    rows = []
    for name in SCORERS:
        challenged = table[f"{name}_challenge"]
        for population, mask in populations.items():
            for bucket in bucket_order:
                stopped = challenged[mask & (table["bucket"] == bucket)].to_numpy()
                metric = "legit_challenge_rate" if population == "legit" else "attack_stop_rate"
                rows.append({"scorer": name, "bucket": bucket, "population": population, "metric": metric,
                             **rate_row(stopped)})
    return pd.DataFrame(rows)


def by_group_table(table: pd.DataFrame, mask: pd.Series, column: str) -> pd.DataFrame:
    rows = []
    for name in SCORERS:
        challenged = table[f"{name}_challenge"]
        for group in sorted(table.loc[mask, column].unique()):
            rows.append({"scorer": name, column: group, **rate_row(challenged[mask & (table[column] == group)].to_numpy())})
    return pd.DataFrame(rows).rename(columns={"rate": "attack_stop_rate"})


def operating_points_table(table: pd.DataFrame, thresholds: dict) -> pd.DataFrame:
    legit = table["kind"] == "legit"
    rows = []
    for name in SCORERS:
        raw = table[f"{name}_raw"]
        for rate, saved in thresholds[name]["operating_points"].items():
            flagged = pd.Series(Threshold(**saved).expected_flags(raw), index=table.index)
            rows.append({"scorer": name, "target_legit_challenge_rate": float(rate),
                         "legit_challenge_rate": flagged[legit].mean(),
                         **{f"{s}_stop_rate": flagged[pick(table)].mean() for s, pick in ATTACK_SETS.items()}})
    return pd.DataFrame(rows)


def latency_table(latency: pd.DataFrame) -> pd.DataFrame:
    grouped = latency.groupby("scorer")["microseconds"]
    table = pd.DataFrame({"samples": grouped.size(), "p50_us": grouped.quantile(0.5),
                          "p95_us": grouped.quantile(0.95), "p99_us": grouped.quantile(0.99)})
    return table.reindex(SCORERS).reset_index()


def labelled_ato_table(scorers: dict, thresholds: dict, bucket_spec: list) -> pd.DataFrame:
    ato = pd.read_parquet(PROCESSED / "features_ato.parquet")
    rows = []
    for name, scorer in scorers.items():
        raw = ato["freeman_raw"].to_numpy() if name == "freeman" else scorer.raw_scores(ato)
        t = thresholds_from_dict(thresholds[name])
        rows.append({"scorer": name, **rate_row(t.otp.expected_flags(raw)), "blocked": t.block.expected_flags(raw).sum(),
                     "with_no_history": int((ato["prior_logins"] == 0).sum())})
    return pd.DataFrame(rows).rename(columns={"rate": "ato_stop_rate"})


def rule_sensitivity_table(table: pd.DataFrame, config: dict) -> pd.DataFrame:
    # Re-run the rule scorer with weights scaled by +-25%, all together and one rule at a time.
    val = pd.read_parquet(PROCESSED / "features_val.parquet")
    val_legit = val["kind"] == "legit"
    test_legit = table["kind"] == "legit"
    base = config["rules"]
    target = config["thresholds"]["target_legit_challenge_rate"]
    variants = {"baseline": base}
    for factor in (0.75, 1.25):
        variants[f"all x{factor}"] = {k: v * factor for k, v in base.items()}
        for key, _, _ in RULES:
            variants[f"{key} x{factor}"] = {**base, key: base[key] * factor}
    rows = []
    for variant, weights in variants.items():
        scorer = RuleScorer(weights)
        threshold = threshold_for_rate(scorer.raw_scores(val[val_legit]), target)
        raw = pd.Series(scorer.raw_scores(table), index=table.index)
        flagged = pd.Series(threshold.expected_flags(raw), index=table.index)
        real = table["kind"] == "attack_ip"
        rows.append({"variant": variant, "threshold": threshold.value, "tie_fraction": threshold.tie_fraction,
                     "legit_challenge_rate": flagged[test_legit].mean(),
                     **{f"{s}_stop_rate": flagged[pick(table)].mean() for s, pick in ATTACK_SETS.items()},
                     "roc_auc_real": roc_auc_score(np.r_[np.zeros(test_legit.sum()), np.ones(real.sum())],
                                                   np.r_[raw[test_legit], raw[real]])})
    return pd.DataFrame(rows)


def feature_tables(table: pd.DataFrame, rforest) -> tuple[pd.DataFrame, pd.DataFrame]:
    # What the Random Forest relies on, and how legitimate logins and real attacks differ on each feature.
    importance = pd.DataFrame({"feature": FEATURES, "importance": rforest.model.feature_importances_})
    means = table[table["kind"].isin(["legit", "attack_ip"])].groupby("kind")[FEATURES].mean().T
    means = means.rename(columns={"legit": "legit_mean", "attack_ip": "real_attack_ip_mean"})
    return importance.sort_values("importance", ascending=False), means.reset_index(names="feature")


def main() -> int:
    config = load_config()
    buckets = config["cold_start_buckets"]
    bucket_order = list(bucket_labels(np.array([low for low, _ in buckets]), buckets))
    scorers = {name: Scorer.load(MODELS / f"{name}.joblib") for name in SCORERS}
    thresholds = json.loads((MODELS / "thresholds.json").read_text())
    started = time.time()

    print("Rebuilding history from the training and validation periods ...")
    history = InMemoryHistory(joblib.load(MODELS / "global_freqs.joblib"))
    for period in ("train", "val"):
        replay(load_period(period), history)

    print("Scoring the test period (real logins + simulated attacks) ...")
    attacks = pd.read_parquet(PROCESSED / "attacks_test.parquet")
    logins = pd.concat([load_period("test"), attacks], ignore_index=True)
    logins = logins.sort_values(["timestamp", "row_id"], kind="stable").reset_index(drop=True)
    table, latency = score_test_period(scorers, history, logins, config["seed"])
    add_scores(table, scorers, thresholds)
    table["bucket"] = bucket_labels(table["prior_logins"].to_numpy(), buckets)
    table.to_parquet(TABLES / "test_scores.parquet", index=False)

    overall = overall_table(table)
    cold_start = cold_start_table(table, bucket_order)
    save_table(overall, "overall.csv")
    save_table(cold_start, "cold_start.csv")
    save_table(by_group_table(table, table["kind"] == "simulated", "attacker_type"), "by_attacker_type.csv")
    save_table(by_group_table(table, table["kind"] == "attack_ip", "context"), "by_attack_context.csv")
    save_table(operating_points_table(table, thresholds), "operating_points.csv")
    save_table(latency_table(latency), "latency.csv")
    save_table(labelled_ato_table(scorers, thresholds, buckets), "labelled_ato.csv")
    save_table(rule_sensitivity_table(table, config), "rule_sensitivity.csv")
    importance, means = feature_tables(table, scorers["rforest"])
    save_table(importance, "rf_feature_importance.csv")
    save_table(means, "feature_means.csv")

    pd.set_option("display.width", 200)
    print("\noverall.csv")
    print(overall.round(4).to_string(index=False))
    print("\ncold_start.csv (stop/challenge rate by prior logins)")
    pivot = cold_start.pivot_table(index=["population", "scorer"], columns="bucket", values="rate")[bucket_order]
    print(pivot.round(3).to_string())
    print(f"\nDone in {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
