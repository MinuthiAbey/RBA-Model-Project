# Measures how long one login takes to score: engine-only for every scorer, and end to end through the demo if it is running.

import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.config import load_config  # noqa: E402
from engine.history import InMemoryHistory  # noqa: E402
from engine.scorers.base import Scorer  # noqa: E402
from research.common import MODELS, SCORERS, classify, load_period, replay, save_table, to_events  # noqa: E402
from service.events import DEMO_AGENTS  # noqa: E402

SAMPLE = 1000
DEMO_URL = "http://127.0.0.1:3000"


def percentiles(values: list[float]) -> dict:
    return {"samples": len(values), "p50": np.percentile(values, 50), "p95": np.percentile(values, 95),
            "p99": np.percentile(values, 99)}


def engine_latency(seed: int) -> list[dict]:
    print("Building login history from the training and validation periods ...")
    history = InMemoryHistory(joblib.load(MODELS / "global_freqs.joblib"))
    for period in ("train", "val"):
        replay(load_period(period), history)
    test = load_period("test")
    test = test[classify(test) == "legit"].sample(SAMPLE, random_state=seed).sort_values("timestamp")
    events = list(to_events(test))

    rows = []
    for name in SCORERS:
        scorer = Scorer.load(MODELS / f"{name}.joblib")
        scorer.score(events[0], history)  # warm-up
        timings = []
        for event in events:
            start = time.perf_counter_ns()
            scorer.score(event, history)
            timings.append((time.perf_counter_ns() - start) / 1000)
        rows.append({"measure": f"engine: {name}", "unit": "microseconds", **percentiles(timings)})
    return rows


def demo_latency() -> list[dict]:
    # A normal sign-in for alice through the web app and the scoring service (HTTP, password hashing, scoring).
    try:
        requests.get(f"{DEMO_URL}/api/events", timeout=2)
    except requests.RequestException:
        print("Demo is not running (start it with `make demo`), skipping the end-to-end measurement.")
        return []
    headers = {"X-Forwarded-For": "192.0.2.10", "User-Agent": DEMO_AGENTS["mac_chrome"], "Origin": DEMO_URL}
    timings = []
    for _ in range(50):
        start = time.perf_counter()
        requests.post(f"{DEMO_URL}/api/login", json={"username": "alice", "password": "demo1234"}, headers=headers)
        timings.append((time.perf_counter() - start) * 1000)
    return [{"measure": "demo: full sign-in request", "unit": "milliseconds", **percentiles(timings)}]


def main() -> int:
    rows = engine_latency(load_config()["seed"]) + demo_latency()
    table = pd.DataFrame(rows)
    save_table(table, "benchmark_latency.csv")
    print("\n" + table.round(1).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
