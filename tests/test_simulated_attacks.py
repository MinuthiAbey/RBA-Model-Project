import numpy as np
import pandas as pd
import pytest

from pipeline import simulate_attacks as attacks


def test_bucket_window():
    logins = np.array([100, 200, 300, 400])
    assert attacks.bucket_window(logins, 0, 0, 0, 1000) == (0, 100)
    assert attacks.bucket_window(logins, 1, 2, 0, 1000) == (100, 300)
    assert attacks.bucket_window(logins, 3, 5, 0, 1000) == (300, 1000)
    assert attacks.bucket_window(logins, 6, 10, 0, 1000) is None
    assert attacks.bucket_window(logins, 1, 2, 500, 1000) is None  # already past bucket before the period starts


def test_victims_meet_minimum_and_are_disjoint():
    rng = np.random.default_rng(0)
    starts = rng.integers(0, 9_000, size=400)
    users = {u: np.sort(rng.integers(starts[u], 10_000, size=rng.integers(1, 30))) for u in range(400)}
    buckets = [(0, 0), (1, 2), (3, 5), (6, None)]
    victims = attacks.choose_victims(users, buckets, 5_000, 10_000, per_bucket=20, rng=rng)
    chosen = [user for entries in victims.values() for user, _ in entries]
    assert all(len(entries) == 20 for entries in victims.values())
    assert len(chosen) == len(set(chosen))


def test_too_few_victims_stops():
    users = {1: np.array([10, 20, 30])}
    with pytest.raises(SystemExit):
        attacks.choose_victims(users, [(21, None)], 0, 100, per_bucket=1, rng=np.random.default_rng(0))


def test_simulated_fields_are_copied_from_real_logins():
    pool = pd.DataFrame({
        "user_id": [1, 1, 2, 3, 4],
        "ip": ["1.1.1.1", "1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"],
        "asn": [10, 10, 20, 30, 40],
        "country": ["NO", "NO", "NO", "BR", "SE"],
        "region": ["-"] * 5, "city": ["-"] * 5, "rtt_ms": [np.nan] * 5,
        "user_agent": ["ua-a", "ua-a", "ua-a2", "ua-b", "ua-c"],
        "browser": ["Chrome", "Chrome", "Chrome", "Firefox", "Safari"],
        "os": ["Win", "Win", "Win", "Linux", "iOS"],
        "device_type": ["desktop", "desktop", "desktop", "desktop", "mobile"],
    })
    victims = {"1-2": [(1, (0, 1_000_000))]}
    result = attacks.simulate(victims, pool, ["naive", "vpn", "targeted"], np.random.default_rng(1))
    by_type = result.set_index("attacker_type")
    assert by_type.loc["vpn", "country"] == "NO" and by_type.loc["targeted", "country"] == "NO"
    assert by_type.loc["targeted", "browser"] == "Chrome" and by_type.loc["targeted", "user_agent"] == "ua-a2"
    assert by_type.loc["vpn", "ip"] == "2.2.2.2"  # same country, but not the victim's own IP
    assert set(zip(result.ip, result.asn, result.country)) <= set(zip(pool.ip, pool.asn, pool.country))
    assert result["is_simulated"].all() and (result["row_id"] < 0).all()
