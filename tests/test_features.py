import math
from datetime import datetime, timedelta

import pytest

from engine.features import FEATURES, extract, typical_hour
from engine.history import GlobalFrequencies, InMemoryHistory


def test_empty_history(make_event):
    f = extract(make_event(), InMemoryHistory())
    assert list(f) == FEATURES
    assert f["prior_logins"] == 0
    assert all(f[name] == 1 for name in FEATURES if name.startswith("new_"))
    assert f["hour_deviation"] == 6
    assert f["days_since_last_login"] == 365
    assert f["user_failures_1h"] == 0
    assert f["ip_distinct_users_1h"] == 0
    assert f["rtt_missing"] == 1 and f["rtt_ms"] == 0


def test_known_context_is_not_new(make_event):
    history = InMemoryHistory()
    history.update(make_event())
    f = extract(make_event(timestamp=datetime(2020, 5, 2, 9, 0)), history)
    assert f["prior_logins"] == 1
    assert all(f[name] == 0 for name in FEATURES if name.startswith("new_"))


@pytest.mark.parametrize("field, value", [
    ("ip", "200.1.1.1"), ("asn", 7018), ("country", "BR"),
    ("browser", "Firefox 90.0"), ("os", "Android 10"), ("device_type", "mobile"),
])
def test_each_new_value_flag(make_event, field, value):
    history = InMemoryHistory()
    history.update(make_event())
    f = extract(make_event(**{field: value}), history)
    assert f[f"new_{field}"] == 1
    assert sum(f[name] for name in FEATURES if name.startswith("new_")) == 1


def test_hour_deviation_wraps_around_midnight(make_event):
    history = InMemoryHistory()
    history.update(make_event(timestamp=datetime(2020, 5, 1, 23, 30)))
    history.update(make_event(timestamp=datetime(2020, 5, 2, 0, 30)))
    typical = typical_hour(history.get_user("alice").hour_counts)
    assert min(typical, 24 - typical) == pytest.approx(0, abs=1e-6)
    f = extract(make_event(timestamp=datetime(2020, 5, 3, 1, 0)), history)
    assert f["hour_deviation"] <= 1.5
    f = extract(make_event(timestamp=datetime(2020, 5, 3, 12, 0)), history)
    assert f["hour_deviation"] >= 11


def test_days_since_last_login_and_cap(make_event):
    history = InMemoryHistory()
    history.update(make_event())
    assert extract(make_event(timestamp=datetime(2020, 5, 4, 9, 0)), history)["days_since_last_login"] == 3
    assert extract(make_event(timestamp=datetime(2022, 1, 1)), history)["days_since_last_login"] == 365


def test_user_failures_last_hour(make_event):
    history = InMemoryHistory()
    now = datetime(2020, 5, 1, 12, 0)
    history.record_attempt(make_event(timestamp=now - timedelta(hours=2), success=False))
    for minutes in (50, 30, 10):
        history.record_attempt(make_event(timestamp=now - timedelta(minutes=minutes), success=False))
    history.record_attempt(make_event(timestamp=now - timedelta(minutes=5), success=True))
    assert extract(make_event(timestamp=now), history)["user_failures_1h"] == 3


def test_ip_distinct_users_last_hour(make_event):
    history = InMemoryHistory()
    now = datetime(2020, 5, 1, 12, 0)
    history.record_attempt(make_event(user_id="old", ip="6.6.6.6", timestamp=now - timedelta(hours=3)))
    for i in range(5):
        history.record_attempt(make_event(user_id=f"u{i}", ip="6.6.6.6", timestamp=now - timedelta(minutes=i + 1)))
    history.record_attempt(make_event(user_id="u0", ip="6.6.6.6", timestamp=now - timedelta(seconds=10)))
    assert extract(make_event(ip="6.6.6.6", timestamp=now), history)["ip_distinct_users_1h"] == 5


def test_global_rarity(make_event):
    freqs = GlobalFrequencies()
    for _ in range(99):
        freqs.add(make_event(country="NO"))
    freqs.add(make_event(country="BR"))
    history = InMemoryHistory(freqs)
    common = extract(make_event(country="NO"), history)["country_global_rarity"]
    rare = extract(make_event(country="BR"), history)["country_global_rarity"]
    unseen = extract(make_event(country="ZZ"), history)["country_global_rarity"]
    # Eq. 8 smoothing: an unseen value is as likely as one seen once.
    assert 0 < common < rare == unseen
    assert common == pytest.approx(-math.log(99 / 101))


def test_rtt_value(make_event):
    f = extract(make_event(rtt_ms=420.0), InMemoryHistory())
    assert f["rtt_missing"] == 0 and f["rtt_ms"] == 420
