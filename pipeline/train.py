# Trains the scorers on the training period, then calibrates them and picks thresholds on the validation period.

import json
import sys
import time
from dataclasses import asdict

import joblib
import numpy as np
import pandas as pd

from engine.calibration import Calibrator
from engine.config import load_config
from engine.decision import choose_thresholds, threshold_for_rate
from engine.features import extract
from engine.history import GlobalFrequencies, InMemoryHistory
from engine.scorers.freeman import FreemanScorer
from engine.scorers.iforest import IsolationForestScorer
from engine.scorers.rforest import RandomForestScorer
from engine.scorers.rules import RuleScorer
from pipeline.common import MODELS, PROCESSED, classify, load_period, replay, save_table, to_events

SCORED_KINDS = ["legit", "attack_ip", "ato"]


def fit_global_frequencies(train: pd.DataFrame) -> GlobalFrequencies:
    freqs = GlobalFrequencies()
    for event in to_events(train[classify(train) == "legit"]):
        freqs.add(event)
    return freqs


def collect_features(logins: pd.DataFrame, history: InMemoryHistory, freeman: FreemanScorer) -> pd.DataFrame:
    """Replays the period and records each scored login's features (and Freeman score) as they were at that moment."""
    kinds = classify(logins)
    rows = []

    def on_event(i: int, event) -> None:
        features = extract(event, history)
        features["freeman_raw"] = freeman.raw_score(event, history)[0]
        features["row"] = i
        rows.append(features)

    replay(logins, history, on_event, np.isin(kinds, SCORED_KINDS))
    table = pd.DataFrame(rows)
    picked = logins.iloc[table.pop("row").to_numpy()]
    table["kind"] = kinds[np.isin(kinds, SCORED_KINDS)]
    for column in ["row_id", "user_id", "timestamp", "success"]:
        table[column] = picked[column].to_numpy()
    return table


def raw_scores(scorers: dict, table: pd.DataFrame) -> dict[str, np.ndarray]:
    return {name: table["freeman_raw"].to_numpy() if name == "freeman" else scorer.raw_scores(table)
            for name, scorer in scorers.items()}


def main() -> int:
    config = load_config()
    seed = config["seed"]
    target = config["thresholds"]
    MODELS.mkdir(parents=True, exist_ok=True)
    started = time.time()

    print("Training period: fitting global frequencies and replaying logins ...")
    train = load_period("train")
    freqs = fit_global_frequencies(train)
    history = InMemoryHistory(freqs)
    freeman = FreemanScorer()
    train_rows = collect_features(train, history, freeman)

    scorers = {
        "rules": RuleScorer(config["rules"]),
        "freeman": freeman,
        "iforest": IsolationForestScorer(config["iforest"]["n_estimators"], seed),
        "rforest": RandomForestScorer(config["rforest"]["n_estimators"], config["rforest"]["class_weight"],
                                      config["rforest"]["min_samples_leaf"], seed),
    }
    legit = train_rows["kind"] == "legit"
    attack = train_rows["kind"] == "attack_ip"
    print(f"Fitting Isolation Forest on {legit.sum():,} legitimate logins ...")
    scorers["iforest"].fit(train_rows[legit])
    print(f"Fitting Random Forest on {legit.sum():,} legitimate logins + {attack.sum():,} attacker-IP attempts ...")
    training_set = train_rows[legit | attack]
    scorers["rforest"].fit(training_set, (training_set["kind"] == "attack_ip").to_numpy(int))

    print("Validation period: replaying logins ...")
    val_rows = collect_features(load_period("val"), history, freeman)
    val_scores = raw_scores(scorers, val_rows)
    val_legit = (val_rows["kind"] == "legit").to_numpy()
    val_attack = (val_rows["kind"] == "attack_ip").to_numpy()

    thresholds, summary = {}, []
    for name, scorer in scorers.items():
        legit_raw = val_scores[name][val_legit]
        scorer.calibrator = Calibrator(legit_raw)
        chosen = choose_thresholds(legit_raw, target["target_legit_challenge_rate"], target["max_legit_block_rate"])
        thresholds[name] = {
            **asdict(chosen),
            "operating_points": {str(rate): asdict(threshold_for_rate(legit_raw, rate))
                                 for rate in target["operating_points"]},
        }
        challenge_rate = float(chosen.otp.expected_flags(legit_raw).mean())
        summary.append({
            "scorer": name,
            "legit_logins": int(val_legit.sum()),
            "legit_challenge_rate": challenge_rate,
            "legit_block_rate": float(chosen.block.expected_flags(legit_raw).mean()),
            "within_half_point_of_target": abs(challenge_rate - target["target_legit_challenge_rate"]) <= 0.005,
            "distinct_legit_scores": int(len(np.unique(legit_raw))),
            "otp_tie_fraction": chosen.otp.tie_fraction,
            "attack_ip_attempts": int(val_attack.sum()),
            "attack_ip_stop_rate": float(chosen.otp.expected_flags(val_scores[name][val_attack]).mean()),
        })
        scorer.save(MODELS / f"{name}.joblib")
        val_rows[f"{name}_raw"] = val_scores[name]

    joblib.dump(freqs, MODELS / "global_freqs.joblib")
    (MODELS / "thresholds.json").write_text(json.dumps(thresholds, indent=2))
    val_rows.to_parquet(PROCESSED / "features_val.parquet", index=False)
    ato_rows = pd.concat([train_rows[train_rows["kind"] == "ato"], val_rows[val_rows["kind"] == "ato"]])
    ato_rows.to_parquet(PROCESSED / "features_ato.parquet", index=False)

    table = pd.DataFrame(summary)
    save_table(table, "validation_rates.csv")
    print(f"\nValidation period (thresholds chosen here; targets: challenge {target['target_legit_challenge_rate']:.1%}, "
          f"block <= {target['max_legit_block_rate']:.1%}):")
    print(table.to_string(index=False))
    print(f"\nSaved models to {MODELS} in {time.time() - started:.0f}s")
    for path in sorted(MODELS.glob("*.joblib")):
        print(f"  {path.name}: {path.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
