from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from engine.features import FEATURES, extract
from engine.history import InMemoryHistory
from engine.scorers.base import Scorer
from engine.scorers.iforest import IsolationForestScorer
from engine.scorers.rforest import RandomForestScorer


def feature_table(n: int, attack: bool, rng: np.random.Generator) -> pd.DataFrame:
    # Hand-made feature rows: legitimate logins are familiar, attacks come from new contexts.
    table = pd.DataFrame(0.0, index=range(n), columns=FEATURES)
    table["prior_logins"] = rng.integers(0, 3, n) if attack else rng.integers(5, 40, n)
    for name in ["new_ip", "new_asn", "new_country", "new_browser", "new_os", "new_device_type"]:
        table[name] = rng.random(n) < (0.9 if attack else 0.05)
    table["hour_deviation"] = rng.uniform(0, 12, n) if attack else rng.uniform(0, 3, n)
    table["days_since_last_login"] = rng.uniform(0, 365 if attack else 30, n)
    table["asn_global_rarity"] = rng.uniform(5, 12, n) if attack else rng.uniform(1, 4, n)
    table["rtt_missing"] = 1.0
    return table.astype(float)


@pytest.fixture
def data():
    rng = np.random.default_rng(42)
    legit, attacks = feature_table(600, False, rng), feature_table(200, True, rng)
    both = pd.concat([legit, attacks], ignore_index=True)
    labels = np.array([0] * len(legit) + [1] * len(attacks))
    return legit, attacks, both, labels


@pytest.fixture
def risky_login(make_event):
    # Alice usually logs in from Norway on a desktop; this login comes from Brazil on a phone at 03:00.
    history = InMemoryHistory()
    for day in range(10):
        history.update(make_event(timestamp=datetime(2020, 5, 1, 9) + timedelta(days=day)))
    event = make_event(timestamp=datetime(2020, 5, 12, 3), ip="200.1.1.1", asn=7018, country="BR",
                       browser="Safari 14", os="iOS 14", device_type="mobile")
    return event, history


def test_isolation_forest_ranks_attacks_higher(data, risky_login):
    legit, attacks, _, _ = data
    scorer = IsolationForestScorer(n_estimators=50, seed=0)
    scorer.fit(legit)
    assert scorer.raw_scores(attacks).mean() > scorer.raw_scores(legit).mean()
    raw, reasons = scorer.raw_score(*risky_login)
    assert np.isfinite(raw) and 1 <= len(reasons) <= 3
    assert [r.weight for r in reasons] == sorted((r.weight for r in reasons), reverse=True)


def test_random_forest_ranks_attacks_higher(data, risky_login):
    legit, attacks, both, labels = data
    scorer = RandomForestScorer(n_estimators=50, class_weight="balanced", min_samples_leaf=1, seed=0)
    scorer.fit(both, labels)
    assert scorer.raw_scores(attacks).mean() > 0.5 > scorer.raw_scores(legit).mean()
    raw, reasons = scorer.raw_score(*risky_login)
    assert 0 <= raw <= 1 and reasons and all(r.weight > 0 for r in reasons)


def test_single_and_batch_scores_agree(data, risky_login):
    _, _, both, labels = data
    scorer = RandomForestScorer(n_estimators=20, class_weight="balanced", min_samples_leaf=1, seed=0)
    scorer.fit(both, labels)
    event, history = risky_login
    single, _ = scorer.raw_score(event, history)
    assert single == pytest.approx(scorer.raw_scores(pd.DataFrame([extract(event, history)]))[0])


def test_save_and_load_round_trip(tmp_path, data):
    legit, attacks, _, _ = data
    scorer = IsolationForestScorer(n_estimators=20, seed=0)
    scorer.fit(legit)
    scorer.save(tmp_path / "iforest.joblib")
    loaded = Scorer.load(tmp_path / "iforest.joblib")
    assert np.allclose(loaded.raw_scores(attacks), scorer.raw_scores(attacks))
