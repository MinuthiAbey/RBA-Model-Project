from datetime import datetime, timedelta

import pandas as pd
import pytest

from engine.config import load_config
from engine.features import extract
from engine.history import InMemoryHistory
from engine.scorers.rules import RuleScorer

WEIGHTS = load_config()["rules"]


@pytest.fixture
def known_history(make_event):
    # Alice has logged in five times at 09:00 from the same context.
    history = InMemoryHistory()
    for day in range(1, 6):
        history.update(make_event(timestamp=datetime(2020, 5, day, 9, 0)))
    return history


def score(event, history):
    return RuleScorer(WEIGHTS).raw_score(event, history)


def test_familiar_login_scores_zero(make_event, known_history):
    raw, reasons = score(make_event(timestamp=datetime(2020, 5, 6, 9, 0)), known_history)
    assert raw == 0 and reasons == []


@pytest.mark.parametrize("field, value, weight_key", [
    ("country", "BR", "new_country"), ("asn", 7018, "new_asn"), ("ip", "200.1.1.1", "new_ip"),
    ("device_type", "mobile", "new_device_type"), ("browser", "Firefox 90.0", "new_browser"),
    ("os", "Android 10", "new_os"),
])
def test_each_new_value_rule(make_event, known_history, field, value, weight_key):
    raw, reasons = score(make_event(timestamp=datetime(2020, 5, 6, 9, 0), **{field: value}), known_history)
    assert raw == WEIGHTS[weight_key]
    assert [r.code for r in reasons] == [f"NEW_{field.upper()}"]


def test_unusual_hour_rule(make_event, known_history):
    raw, reasons = score(make_event(timestamp=datetime(2020, 5, 6, 21, 30)), known_history)
    assert raw == WEIGHTS["unusual_hour"]
    assert reasons[0].text == "unusual hour 21:30"


def test_failures_rule(make_event, known_history):
    now = datetime(2020, 5, 6, 9, 0)
    for minutes in (20, 10, 5):
        known_history.record_attempt(make_event(timestamp=now - timedelta(minutes=minutes), success=False))
    raw, _ = score(make_event(timestamp=now), known_history)
    assert raw == WEIGHTS["user_failures_1h_ge_3"]


def test_ip_many_accounts_rule(make_event, known_history):
    now = datetime(2020, 5, 6, 9, 0)
    for i in range(5):
        known_history.record_attempt(make_event(user_id=f"victim{i}", timestamp=now - timedelta(minutes=i + 1)))
    raw, _ = score(make_event(timestamp=now), known_history)
    assert raw == WEIGHTS["ip_distinct_users_1h_ge_5"]


def test_total_is_capped_and_reasons_sorted(make_event):
    raw, reasons = score(make_event(), InMemoryHistory())
    assert raw == 100
    assert sum(r.weight for r in reasons) > 100
    assert [r.weight for r in reasons] == sorted((r.weight for r in reasons), reverse=True)
    assert reasons[0].code == "NEW_COUNTRY"


def test_batch_matches_single(make_event, known_history):
    events = [make_event(timestamp=datetime(2020, 5, 6, h, 0), country=c) for h, c in [(9, "NO"), (3, "BR"), (12, "SE")]]
    features = pd.DataFrame([extract(e, known_history) for e in events])
    batch = RuleScorer(WEIGHTS).raw_scores(features)
    assert list(batch) == [score(e, known_history)[0] for e in events]
