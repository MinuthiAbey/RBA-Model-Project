# Converts the raw CSV to Parquet, samples users and splits the logins by time into train/val/test.

import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.config import PROJECT_ROOT, load_config  # noqa: E402

RAW_CSV = PROJECT_ROOT / "data" / "raw" / "rba-dataset.csv"
PROCESSED = PROJECT_ROOT / "data" / "processed"
FULL_PARQUET = PROCESSED / "rba-full.parquet"
TABLES = PROJECT_ROOT / "results" / "tables"

COLUMNS = {
    "index": "row_id",
    "Login Timestamp": "timestamp",
    "User ID": "user_id",
    "Round-Trip Time [ms]": "rtt_ms",
    "IP Address": "ip",
    "Country": "country",
    "Region": "region",
    "City": "city",
    "ASN": "asn",
    "User Agent String": "user_agent",
    "Browser Name and Version": "browser",
    "OS Name and Version": "os",
    "Device Type": "device_type",
    "Login Successful": "success",
    "Is Attack IP": "is_attack_ip",
    "Is Account Takeover": "is_ato",
}
TEXT_COLUMNS = {"ip", "country", "region", "city", "user_agent", "browser", "os", "device_type"}
COLUMN_TYPES = {"timestamp": "TIMESTAMP", "rtt_ms": "DOUBLE", "success": "BOOLEAN",
                "is_attack_ip": "BOOLEAN", "is_ato": "BOOLEAN"}

LOGIN_COUNT_BINS = [(1, 1), (2, 2), (3, 5), (6, 10), (11, 20), (21, 50), (51, 100), (101, None)]


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("SET memory_limit = '6GB'")
    con.execute(f"SET temp_directory = '{PROCESSED / 'duckdb_tmp'}'")
    return con


def csv_to_parquet(con: duckdb.DuckDBPyConnection) -> None:
    if FULL_PARQUET.exists():
        print(f"{FULL_PARQUET.name} already exists, skipping CSV conversion.")
        return
    header = [row[0] for row in con.execute(f"DESCRIBE SELECT * FROM read_csv('{RAW_CSV}')").fetchall()]
    missing = [name for name in COLUMNS if name not in header]
    if missing:
        raise SystemExit(f"CSV is missing expected columns {missing}. Header: {header}")

    select = []
    for original, name in COLUMNS.items():
        if name in TEXT_COLUMNS:
            select.append(f"""NULLIF("{original}", '') AS {name}""")
        else:
            select.append(f"""CAST("{original}" AS {COLUMN_TYPES.get(name, 'BIGINT')}) AS {name}""")
    print("Converting CSV to Parquet (one-off) ...")
    con.execute(f"COPY (SELECT {', '.join(select)} FROM read_csv('{RAW_CSV}')) "
                f"TO '{FULL_PARQUET}' (FORMAT parquet, COMPRESSION zstd)")


def sample_user_ids(con: duckdb.DuckDBPyConnection, n_users: int, seed: int) -> np.ndarray:
    all_ids = con.execute(f"SELECT DISTINCT user_id FROM '{FULL_PARQUET}' ORDER BY user_id").fetchnumpy()["user_id"]
    sampled = np.random.default_rng(seed).choice(all_ids, size=min(n_users, len(all_ids)), replace=False)
    # Labelled account takeovers are so rare that every affected user is added for the ATO case study.
    ato_ids = con.execute(f"SELECT DISTINCT user_id FROM '{FULL_PARQUET}' WHERE is_ato").fetchnumpy()["user_id"]
    return np.union1d(sampled, ato_ids)


def bin_label(low: int, high: int | None) -> str:
    if high is None:
        return f"{low}+"
    return str(low) if low == high else f"{low}-{high}"


def login_count_table(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    def users_per_bin(source: str) -> list[int]:
        per_user = con.execute(f"SELECT COUNT(*) AS n FROM {source} GROUP BY user_id").fetchnumpy()["n"]
        return [int(((per_user >= low) & (per_user <= (high or per_user.max()))).sum())
                for low, high in LOGIN_COUNT_BINS]

    sample, population = users_per_bin("sample"), users_per_bin(f"'{FULL_PARQUET}'")
    return pd.DataFrame({
        "logins_per_user": [bin_label(low, high) for low, high in LOGIN_COUNT_BINS],
        "sample_users": sample,
        "sample_pct": np.round(100 * np.array(sample) / sum(sample), 2),
        "population_users": population,
        "population_pct": np.round(100 * np.array(population) / sum(population), 2),
    })


def main() -> int:
    if not RAW_CSV.exists() and not FULL_PARQUET.exists():
        print(f"{RAW_CSV} not found. Run research/01_download.py first.", file=sys.stderr)
        return 1
    config = load_config()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    con = connect()
    csv_to_parquet(con)

    user_ids = sample_user_ids(con, config["sample_users"], config["seed"])
    con.register("sampled_ids", pd.DataFrame({"user_id": user_ids}))
    con.execute(f"CREATE TABLE sample AS SELECT * FROM '{FULL_PARQUET}' "
                "WHERE user_id IN (SELECT user_id FROM sampled_ids)")
    n_logins = con.execute("SELECT COUNT(*) FROM sample").fetchone()[0]
    print(f"Sampled {len(user_ids):,} users, {n_logins:,} logins")

    stats = login_count_table(con)
    stats.to_csv(TABLES / "sample_stats.csv", index=False)
    print("\nLogins per user (sample vs full dataset):")
    print(stats.to_string(index=False))

    train_share = config["splits"]["train"]
    t_val, t_test = con.execute("SELECT quantile_disc(timestamp, ?), quantile_disc(timestamp, ?) FROM sample",
                                [train_share, train_share + config["splits"]["val"]]).fetchone()
    periods = {
        "train": f"timestamp < TIMESTAMP '{t_val}'",
        "val": f"timestamp >= TIMESTAMP '{t_val}' AND timestamp < TIMESTAMP '{t_test}'",
        "test": f"timestamp >= TIMESTAMP '{t_test}'",
    }

    rows = []
    for name, where in periods.items():
        path = PROCESSED / f"{name}.parquet"
        con.execute(f"COPY (SELECT * FROM sample WHERE {where} ORDER BY timestamp, row_id) "
                    f"TO '{path}' (FORMAT parquet)")
        rows.append(con.execute(f"""
            SELECT '{name}', COUNT(*), MIN(timestamp), MAX(timestamp),
                   COUNT(*) FILTER (WHERE NOT is_attack_ip AND NOT is_ato AND success),
                   COUNT(*) FILTER (WHERE NOT is_attack_ip AND NOT is_ato AND NOT success),
                   COUNT(*) FILTER (WHERE is_attack_ip),
                   COUNT(*) FILTER (WHERE is_attack_ip AND success),
                   COUNT(*) FILTER (WHERE is_ato)
            FROM '{path}'""").fetchone())
    split_stats = pd.DataFrame(rows, columns=["period", "logins", "first", "last", "legit_success",
                                              "legit_failed", "attack_ip", "attack_ip_success", "ato"])
    split_stats.to_csv(TABLES / "split_stats.csv", index=False)
    print(f"\nSplit boundaries: val starts {t_val}, test starts {t_test}\n")
    print(split_stats.to_string(index=False))

    overlap_free = (split_stats["last"].iloc[:-1].values < split_stats["first"].iloc[1:].values).all()
    print(f"\nPeriods overlap-free: {overlap_free}")
    return 0 if overlap_free else 1


if __name__ == "__main__":
    sys.exit(main())
