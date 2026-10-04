from datetime import datetime, timedelta

from engine.history import InMemoryHistory
from engine.trust import apply_trust
from engine.types import Decision

NOW = datetime(2020, 5, 10, 9, 0)


def test_only_a_verified_context_skips_the_code(make_event):
    history = InMemoryHistory()
    poland = make_event(country="PL", asn=205727, timestamp=NOW)
    assert apply_trust(Decision.OTP, poland, history) == (Decision.OTP, None, None)
    history.trust(make_event(country="PL", asn=205727, timestamp=NOW - timedelta(days=2)))
    assert apply_trust(Decision.OTP, poland, history) == (Decision.ALLOW, NOW - timedelta(days=2), None)


def test_trust_needs_the_exact_context(make_event):
    history = InMemoryHistory()
    history.trust(make_event(country="PL", asn=205727, timestamp=NOW - timedelta(days=1)))
    other_network = make_event(country="PL", asn=49528, timestamp=NOW)
    other_device = make_event(country="PL", asn=205727, user_agent="something else", timestamp=NOW)
    assert apply_trust(Decision.OTP, other_network, history)[0] is Decision.OTP
    assert apply_trust(Decision.OTP, other_device, history)[0] is Decision.OTP


def test_trust_expires_and_never_relaxes_a_block(make_event):
    history = InMemoryHistory()
    history.trust(make_event(country="PL", timestamp=NOW - timedelta(days=31)))
    assert apply_trust(Decision.OTP, make_event(country="PL", timestamp=NOW), history)[0] is Decision.OTP
    history.trust(make_event(country="PL", timestamp=NOW - timedelta(days=1)))
    assert apply_trust(Decision.BLOCK, make_event(country="PL", timestamp=NOW), history)[0] is Decision.BLOCK


def test_trust_is_ignored_when_something_else_is_wrong(make_event):
    history = InMemoryHistory()
    history.trust(make_event(country="PL", timestamp=NOW - timedelta(days=1)))
    history.record_attempt(make_event(country="PL", success=False, timestamp=NOW - timedelta(minutes=5)))
    assert apply_trust(Decision.OTP, make_event(country="PL", timestamp=NOW), history) == \
        (Decision.OTP, None, "1 wrong password in the last hour")
