import math
from datetime import datetime, timedelta

import pytest

from engine.history import GlobalFrequencies, InMemoryHistory
from engine.scorers.freeman import FreemanScorer

ALICE = dict(user_id="alice", ip="A", asn=1, country="NO", user_agent="ua1",
             browser="Chrome", os="Win", device_type="desktop")
BOB = dict(user_id="bob", ip="C", asn=2, country="SE", user_agent="ua2",
           browser="Firefox", os="Linux", device_type="mobile")


@pytest.fixture
def history(make_event):
    # Alice: 3 logins (IP A twice, IP B once, same browser). Bob: 1 login. Global counts come from the same 4 logins.
    logins = [make_event(**ALICE), make_event(**{**ALICE, "ip": "B"}), make_event(**ALICE), make_event(**BOB)]
    freqs = GlobalFrequencies()
    store = InMemoryHistory(freqs)
    for i, login in enumerate(logins):
        login.timestamp = datetime(2020, 5, 1) + timedelta(days=i)
        freqs.add(login)
        store.update(login)
    return store


def test_worked_example_familiar_login(make_event, history):
    raw, _ = FreemanScorer().raw_score(make_event(**ALICE), history)
    # IP family:  global = c(A)/(N+1) = 2/5,  local = (0.6*2 + 0.3*3 + 0.1*3)/3 = 0.8
    # UA family:  global = c(ua1)/(N+1) = 3/5, local = 1.0
    # User term:  p(u|A)/p(u|L) = (1/2) / ((3+1)/(4+2)) = 0.75
    assert raw == pytest.approx(math.log(0.4 / 0.8 * 0.6 / 1.0 * 0.75))


def test_worked_example_new_network(make_event, history):
    raw, reasons = FreemanScorer().raw_score(make_event(**{**ALICE, "ip": "D", "asn": 2, "country": "SE"}), history)
    # IP family: unseen IP D -> global = 0.6*(1/5) + 0.3*(1/(2*5)) + 0.1*(1/(2*5)) = 0.16
    # Alice has never used IP D, AS2 or SE, so local = global/4 and the term is log 4.
    assert raw == pytest.approx(math.log(4 * 0.6 / 1.0 * 0.75))
    assert reasons[0].code == "UNUSUAL_IP" and reasons[0].text == "new country NO -> SE"
    assert reasons[0].weight == pytest.approx(math.log(4))


def test_familiar_scores_lower_than_entirely_new(make_event, history):
    scorer = FreemanScorer()
    familiar, _ = scorer.raw_score(make_event(**ALICE), history)
    new_country, _ = scorer.raw_score(make_event(**{**ALICE, "ip": "Z", "asn": 9, "country": "BR"}), history)
    all_new, _ = scorer.raw_score(make_event(**{**ALICE, **{k: v for k, v in BOB.items() if k != "user_id"}}), history)
    assert familiar < new_country < all_new


@pytest.mark.parametrize("overrides", [
    {}, {"user_id": "newcomer"}, {"ip": None, "asn": None, "country": None, "device_type": None},
    {"user_id": "x", "ip": "?", "asn": 999, "country": "ZZ", "user_agent": "?", "browser": "?", "os": "?"},
])
def test_scores_are_always_finite(make_event, history, overrides):
    raw, _ = FreemanScorer().raw_score(make_event(**{**ALICE, **overrides}), history)
    assert math.isfinite(raw)


def test_finite_with_no_data_at_all(make_event):
    raw, _ = FreemanScorer().raw_score(make_event(), InMemoryHistory())
    assert math.isfinite(raw)


def test_brand_new_users_tie_and_do_not_drift(make_event, history):
    # Same evidence (no history) must give the same score, however much the service has grown since training.
    first, _ = FreemanScorer().raw_score(make_event(**{**ALICE, "user_id": "new1"}), history)
    history.update(make_event(**BOB))
    second, _ = FreemanScorer().raw_score(make_event(**{**BOB, "user_id": "new2", "ip": "Q"}), history)
    assert first == second
