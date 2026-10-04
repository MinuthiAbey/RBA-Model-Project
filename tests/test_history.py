import random
from datetime import datetime, timedelta

from engine.features import extract
from engine.history import InMemoryHistory


def test_unknown_user_is_empty_and_not_stored():
    history = InMemoryHistory()
    assert history.get_user("nobody").login_count == 0
    assert "nobody" not in history.users


def test_record_attempt_does_not_teach_history(make_event):
    history = InMemoryHistory()
    history.record_attempt(make_event(success=False))
    history.record_attempt(make_event(success=True))
    assert history.get_user("alice").login_count == 0


def test_update_only_touches_that_user(make_event):
    history = InMemoryHistory()
    history.update(make_event(user_id="alice"))
    assert history.get_user("alice").login_count == 1
    assert history.get_user("bob").login_count == 0
    assert history.total_logins == 1


def test_no_future_leakage(make_event):
    # Scoring then updating in time order must give exactly the features of a history built only from earlier logins.
    rng = random.Random(42)
    start = datetime(2020, 1, 1)
    events = [make_event(user_id=rng.choice(["a", "b", "c"]),
                         timestamp=start + timedelta(minutes=17 * i),
                         ip=f"10.0.0.{rng.randint(1, 4)}",
                         country=rng.choice(["NO", "SE", "BR"]),
                         device_type=rng.choice(["desktop", "mobile"]),
                         success=rng.random() > 0.3)
              for i in range(60)]

    streamed = InMemoryHistory()
    for i, event in enumerate(events):
        features = extract(event, streamed)

        rebuilt = InMemoryHistory()
        for earlier in events[:i]:
            if earlier.success:
                rebuilt.update(earlier)
            rebuilt.record_attempt(earlier)
        assert features == extract(event, rebuilt)

        if event.success:
            streamed.update(event)
        streamed.record_attempt(event)
