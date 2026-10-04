# Helpers shared by the training and evaluation scripts.

import math
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import numpy as np
import pandas as pd

from engine.config import PROJECT_ROOT, configured_path
from engine.history import HistoryStore
from engine.types import LoginEvent

PROCESSED = configured_path("data") / "processed"
MODELS = PROJECT_ROOT / "models"
TABLES = configured_path("results") / "tables"
FIGURES = configured_path("results") / "figures"
SCORERS = ["rules", "freeman", "iforest", "rforest"]


def load_period(name: str) -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / f"{name}.parquet")


def classify(logins: pd.DataFrame) -> np.ndarray:
    simulated = logins["is_simulated"].fillna(False).to_numpy(bool) if "is_simulated" in logins else False
    return np.select(
        [simulated, logins["is_ato"].to_numpy(bool), logins["is_attack_ip"].to_numpy(bool), logins["success"].to_numpy(bool)],
        ["simulated", "ato", "attack_ip", "legit"],
        "legit_failed",
    )


def _text(value) -> str | None:
    return value if isinstance(value, str) else None


def to_events(logins: pd.DataFrame) -> Iterator[LoginEvent]:
    for row in logins.itertuples(index=False):
        yield LoginEvent(
            user_id=str(row.user_id), timestamp=row.timestamp, ip=_text(row.ip), country=_text(row.country),
            asn=None if pd.isna(row.asn) else int(row.asn), user_agent=_text(row.user_agent),
            browser=_text(row.browser), os=_text(row.os), device_type=_text(row.device_type),
            rtt_ms=None if math.isnan(row.rtt_ms) else float(row.rtt_ms), success=bool(row.success),
        )


def replay(logins: pd.DataFrame, history: HistoryStore,
           on_event: Callable[[int, LoginEvent], None] | None = None, score_mask: np.ndarray | None = None) -> None:
    """Walks logins in time order: score first, then let the history learn (spec rule: score, then update)."""
    classes = classify(logins)
    started = time.time()
    for i, (event, kind) in enumerate(zip(to_events(logins), classes)):
        if on_event and (score_mask is None or score_mask[i]):
            on_event(i, event)
        if kind == "legit":
            history.update(event)
        if kind != "simulated":
            history.record_attempt(event)
        if (i + 1) % 200_000 == 0:
            print(f"  {i + 1:,} / {len(logins):,} logins ({time.time() - started:.0f}s)")


def save_table(table: pd.DataFrame, name: str) -> Path:
    TABLES.mkdir(parents=True, exist_ok=True)
    path = TABLES / name
    table.to_csv(path, index=False)
    return path
