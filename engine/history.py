from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Protocol

from engine.types import LoginEvent

# Login context remembered per user and counted globally.
CONTEXT_FIELDS = ("ip", "asn", "country", "user_agent", "browser", "os", "device_type")
VELOCITY_WINDOW = timedelta(hours=1)


@dataclass
class UserHistory:
    login_count: int = 0
    seen: dict[str, Counter] = field(default_factory=lambda: {name: Counter() for name in CONTEXT_FIELDS})
    hour_counts: list[int] = field(default_factory=lambda: [0] * 24)
    last_login: datetime | None = None
    # Contexts the user proved with a one-time code: (country, network, user agent) -> when.
    trusted: dict[tuple, datetime] = field(default_factory=dict)

    def most_common(self, field_name: str) -> Any:
        top = self.seen[field_name].most_common(1)
        return top[0][0] if top else None


def trusted_key(event: LoginEvent) -> tuple:
    return (event.country, event.asn, event.user_agent)


class GlobalFrequencies:
    """How often each context value appears across all users' training logins."""

    def __init__(self) -> None:
        self.counts = {name: Counter() for name in CONTEXT_FIELDS}
        self.total = 0
        self.users: set[str] = set()

    def add(self, event: LoginEvent) -> None:
        for name in CONTEXT_FIELDS:
            self.counts[name][getattr(event, name)] += 1
        self.total += 1
        self.users.add(event.user_id)

    def count(self, field_name: str, value: Any) -> int:
        return self.counts[field_name][value]

    def freq(self, field_name: str, value: Any) -> float:
        # Freeman et al. (2016) Eq. 8 with one unseen value: unseen gets 1/(N+1), seen c/(N+1).
        return max(self.counts[field_name][value], 1) / (self.total + 1)


class HistoryStore(Protocol):
    global_freqs: GlobalFrequencies
    total_logins: int

    def get_user(self, user_id: str) -> UserHistory: ...
    def update(self, event: LoginEvent) -> None: ...
    def trust(self, event: LoginEvent) -> None: ...
    def record_attempt(self, event: LoginEvent) -> None: ...
    def failures_last_hour(self, user_id: str, now: datetime) -> int: ...
    def ip_users_last_hour(self, ip: str, now: datetime) -> int: ...
    def global_freq(self, field_name: str, value: Any) -> float: ...


class InMemoryHistory:
    """History kept in dictionaries. Used by the research pipeline, which replays logins in time order."""

    def __init__(self, global_freqs: GlobalFrequencies | None = None) -> None:
        self.users: dict[str, UserHistory] = {}
        self.global_freqs = global_freqs or GlobalFrequencies()
        self.total_logins = 0
        self._failures: dict[str, deque[datetime]] = {}
        self._ip_attempts: dict[str, deque[tuple[datetime, str]]] = {}
        self._ip_users: dict[str, Counter] = {}

    def get_user(self, user_id: str) -> UserHistory:
        return self.users.get(user_id) or UserHistory()

    def update(self, event: LoginEvent) -> None:
        # Only for legitimate successful logins: this is what the engine learns as "normal".
        user = self.users.setdefault(event.user_id, UserHistory())
        user.login_count += 1
        for name in CONTEXT_FIELDS:
            user.seen[name][getattr(event, name)] += 1
        user.hour_counts[event.timestamp.hour] += 1
        user.last_login = event.timestamp
        self.total_logins += 1

    def trust(self, event: LoginEvent) -> None:
        # Called only after the user passed a one-time code for this login.
        self.users.setdefault(event.user_id, UserHistory()).trusted[trusted_key(event)] = event.timestamp

    def record_attempt(self, event: LoginEvent) -> None:
        # Every observed attempt, attacks included, feeds the one-hour velocity counters.
        if event.success is False:
            self._failures.setdefault(event.user_id, deque()).append(event.timestamp)
        self._ip_attempts.setdefault(event.ip, deque()).append((event.timestamp, event.user_id))
        self._ip_users.setdefault(event.ip, Counter())[event.user_id] += 1

    def failures_last_hour(self, user_id: str, now: datetime) -> int:
        times = self._failures.get(user_id)
        if not times:
            return 0
        while times and times[0] < now - VELOCITY_WINDOW:
            times.popleft()
        return len(times)

    def ip_users_last_hour(self, ip: str, now: datetime) -> int:
        attempts = self._ip_attempts.get(ip)
        if not attempts:
            return 0
        users = self._ip_users[ip]
        while attempts and attempts[0][0] < now - VELOCITY_WINDOW:
            _, user_id = attempts.popleft()
            users[user_id] -= 1
            if users[user_id] == 0:
                del users[user_id]
        return len(users)

    def global_freq(self, field_name: str, value: Any) -> float:
        return self.global_freqs.freq(field_name, value)
