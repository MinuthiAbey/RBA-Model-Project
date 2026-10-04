# Builds simulated account-takeover attempts for a separate, clearly labelled test-period experiment.
# Every field is copied from a real login in the sample, and these rows never enter any user's history.

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.config import configured_path, load_config  # noqa: E402

PROCESSED = configured_path("data") / "processed"
TABLES = configured_path("results") / "tables"
OUTPUT = PROCESSED / "attacks_test.parquet"

NETWORK = ["ip", "asn", "country", "region", "city", "rtt_ms"]
DEVICE = ["user_agent", "browser", "os", "device_type"]
DEVICE_KEY = ["browser", "os", "device_type"]


def to_us(timestamps: pd.Series) -> np.ndarray:
    return timestamps.astype("datetime64[us]").astype("int64").to_numpy()


def bucket_label(low: int, high: int | None) -> str:
    if high is None:
        return f"{low}+"
    return str(low) if low == high else f"{low}-{high}"


def bucket_window(login_us: np.ndarray, low: int, high: int | None, start: int, end: int) -> tuple[int, int] | None:
    """Open time range within [start, end) in which the user has between low and high earlier logins."""
    if low > len(login_us):
        return None
    begin = start if low == 0 else max(start, int(login_us[low - 1]))
    finish = end if high is None or high >= len(login_us) else min(end, int(login_us[high]))
    return (begin, finish) if finish - begin > 2 else None


def choose_victims(login_us_by_user: dict, buckets: list, start: int, end: int,
                   per_bucket: int, rng: np.random.Generator) -> dict[str, list[tuple]]:
    # Scarcest buckets pick first, and nobody is a victim in two buckets.
    used: set = set()
    victims = {}
    for low, high in reversed(buckets):
        eligible = []
        for user in sorted(login_us_by_user):
            if user in used:
                continue
            window = bucket_window(login_us_by_user[user], low, high, start, end)
            if window:
                eligible.append((user, window))
        label = bucket_label(low, high)
        if len(eligible) < per_bucket:
            raise SystemExit(f"Bucket {label}: only {len(eligible)} possible victims, need {per_bucket}.")
        picked = rng.choice(len(eligible), size=per_bucket, replace=False)
        victims[label] = [eligible[i] for i in sorted(picked)]
        used.update(user for user, _ in victims[label])
    return victims


def most_common_per_user(logins: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    counts = logins.groupby(["user_id", *columns], dropna=False).size().rename("n").reset_index()
    counts = counts.sort_values(["user_id", "n", *columns], ascending=[True, False, *[True] * len(columns)])
    return counts.drop_duplicates("user_id").set_index("user_id")[columns]


def pick_row(candidates: np.ndarray, pool_users: np.ndarray, victim, rng: np.random.Generator) -> int:
    # Prefer another user's login so the attacker doesn't accidentally reuse the victim's own IP or browser.
    for _ in range(20):
        row = int(candidates[rng.integers(len(candidates))])
        if pool_users[row] != victim:
            return row
    return row


def simulate(victims: dict, pool: pd.DataFrame, types: list[str], rng: np.random.Generator) -> pd.DataFrame:
    pool = pool.reset_index(drop=True)
    pool_users = pool["user_id"].to_numpy()
    all_rows = np.arange(len(pool))
    by_country = pool.groupby("country").indices
    by_device = pool.groupby(DEVICE_KEY).indices
    home_country = most_common_per_user(pool, ["country"])["country"]
    home_device = most_common_per_user(pool, DEVICE_KEY)

    records = []
    for label, entries in victims.items():
        for victim, (begin, finish) in entries:
            country_rows = by_country.get(home_country[victim], all_rows)
            device_rows = by_device.get(tuple(home_device.loc[victim]), all_rows)
            for attacker_type in types:
                network_rows = all_rows if attacker_type == "naive" else country_rows
                same_device = attacker_type == "targeted"
                network = pool.iloc[pick_row(network_rows, pool_users, victim, rng)]
                device = pool.iloc[pick_row(device_rows if same_device else all_rows, pool_users, victim, rng)]
                records.append({
                    "timestamp_us": int(rng.integers(begin + 1, finish)),
                    "user_id": victim,
                    **network[NETWORK].to_dict(),
                    **device[DEVICE].to_dict(),
                    "success": True,
                    "attacker_type": attacker_type,
                    "target_bucket": label,
                })
    attacks = pd.DataFrame(records)
    attacks.insert(0, "timestamp", pd.to_datetime(attacks.pop("timestamp_us"), unit="us"))
    attacks.insert(0, "row_id", -np.arange(1, len(attacks) + 1))  # negative ids can never clash with dataset rows
    attacks["is_attack_ip"] = False
    attacks["is_ato"] = False
    attacks["is_simulated"] = True
    return attacks.sort_values(["timestamp", "row_id"]).reset_index(drop=True)


def prior_logins(attacks: pd.DataFrame, login_us_by_user: dict) -> np.ndarray:
    attack_us = to_us(attacks["timestamp"])
    return np.array([np.searchsorted(login_us_by_user[user], t, side="left")
                     for user, t in zip(attacks["user_id"], attack_us)])


def main() -> int:
    config = load_config()
    rng = np.random.default_rng(config["seed"])
    buckets = [(low, high) for low, high in config["cold_start_buckets"]]
    per_bucket = config["attacks"]["min_attacks_per_bucket"]
    types = config["attacks"]["types"]

    logins = pd.concat([pd.read_parquet(PROCESSED / f"{p}.parquet") for p in ("train", "val", "test")],
                       ignore_index=True)
    legit = logins[~logins["is_attack_ip"] & ~logins["is_ato"] & logins["success"]]
    test = pd.read_parquet(PROCESSED / "test.parquet", columns=["timestamp"])
    start, end = int(to_us(test["timestamp"]).min()), int(to_us(test["timestamp"]).max()) + 1

    login_us_by_user = {user: np.sort(to_us(group)) for user, group in legit.groupby("user_id")["timestamp"]}

    victims = choose_victims(login_us_by_user, buckets, start, end, per_bucket, rng)
    attacks = simulate(victims, legit, types, rng)
    attacks.to_parquet(OUTPUT, index=False)

    # Check: every attack lands in the bucket it was built for, and victims are unique per bucket.
    actual = prior_logins(attacks, login_us_by_user)
    expected = {bucket_label(low, high): (low, high if high is not None else np.inf) for low, high in buckets}
    in_bucket = [expected[b][0] <= n <= expected[b][1] for b, n in zip(attacks["target_bucket"], actual)]
    victims_per_bucket = attacks.groupby("target_bucket")["user_id"].nunique()
    distinct_victims = attacks["user_id"].nunique() == victims_per_bucket.sum()

    counts = attacks.pivot_table(index="target_bucket", columns="attacker_type", values="row_id",
                                 aggfunc="count").reindex(list(expected))[types]
    counts["victims"] = victims_per_bucket.reindex(list(expected))
    counts.index.name = "bucket"
    counts.reset_index().to_csv(TABLES / "simulated_attack_counts.csv", index=False)

    print(f"Simulated attacks in the test period: {len(attacks):,} -> {OUTPUT.name}\n")
    print(counts.to_string())
    print(f"\nEvery attack in its intended bucket: {all(in_bucket)}")
    print(f"No victim reused across buckets: {distinct_victims}")
    print(f"Every bucket has >= {per_bucket} per type: {bool((counts[types] >= per_bucket).all().all())}")
    print(f"Attack timestamps within test period: {attacks['timestamp'].min()} .. {attacks['timestamp'].max()}")
    return 0 if all(in_bucket) and distinct_victims else 1


if __name__ == "__main__":
    sys.exit(main())
