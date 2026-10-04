from datetime import datetime

import pytest

from engine.types import LoginEvent


@pytest.fixture
def make_event():
    # Builds a login with sensible defaults; tests override only what they care about.
    def make(**overrides) -> LoginEvent:
        values = dict(user_id="alice", timestamp=datetime(2020, 5, 1, 9, 0), ip="81.0.0.1", country="NO",
                      asn=29695, user_agent="Mozilla/5.0 (Windows NT 10.0) Chrome/80.0", browser="Chrome 80.0",
                      os="Windows 10", device_type="desktop", rtt_ms=None, success=True)
        values.update(overrides)
        return LoginEvent(**values)
    return make
