import math
from datetime import datetime

from engine.history import HistoryStore
from engine.types import LoginEvent

NEW_VALUE_FIELDS = ("ip", "asn", "country", "browser", "os", "device_type")
FEATURES = [
    "prior_logins",
    *(f"new_{name}" for name in NEW_VALUE_FIELDS),
    "hour_deviation",
    "days_since_last_login",
    "user_failures_1h",
    "ip_distinct_users_1h",
    "asn_global_rarity",
    "country_global_rarity",
    "ua_global_rarity",
    "rtt_missing",
    "rtt_ms",
]
NO_HISTORY_HOUR_DEVIATION = 6.0
MAX_DAYS = 365.0

# Centre of each hour on the 24-hour clock, as an angle.
_HOUR_ANGLES = [2 * math.pi * (hour + 0.5) / 24 for hour in range(24)]


def extract(event: LoginEvent, history: HistoryStore) -> dict[str, float]:
    """Feature vector for one login, using only history recorded before it."""
    user = history.get_user(event.user_id)
    features = {"prior_logins": float(user.login_count)}
    for name in NEW_VALUE_FIELDS:
        features[f"new_{name}"] = float(getattr(event, name) not in user.seen[name])
    features["hour_deviation"] = hour_deviation(event.timestamp, user.hour_counts)
    features["days_since_last_login"] = days_since(event.timestamp, user.last_login)
    features["user_failures_1h"] = float(history.failures_last_hour(event.user_id, event.timestamp))
    features["ip_distinct_users_1h"] = float(history.ip_users_last_hour(event.ip, event.timestamp))
    features["asn_global_rarity"] = -math.log(history.global_freq("asn", event.asn))
    features["country_global_rarity"] = -math.log(history.global_freq("country", event.country))
    features["ua_global_rarity"] = (-math.log(history.global_freq("browser", event.browser))
                                    - math.log(history.global_freq("os", event.os)))
    features["rtt_missing"] = float(event.rtt_ms is None)
    features["rtt_ms"] = event.rtt_ms if event.rtt_ms is not None else 0.0
    return features


def typical_hour(hour_counts: list[int]) -> float | None:
    # Circular mean, so a user who logs in at 23:00 and 01:00 is typical around midnight, not noon.
    x = sum(count * math.cos(angle) for count, angle in zip(hour_counts, _HOUR_ANGLES))
    y = sum(count * math.sin(angle) for count, angle in zip(hour_counts, _HOUR_ANGLES))
    if math.hypot(x, y) < 1e-9:
        return None
    return (math.atan2(y, x) * 24 / (2 * math.pi)) % 24


def hour_deviation(timestamp: datetime, hour_counts: list[int]) -> float:
    typical = typical_hour(hour_counts)
    if typical is None:
        return NO_HISTORY_HOUR_DEVIATION
    diff = abs(timestamp.hour + timestamp.minute / 60 - typical) % 24
    return min(diff, 24 - diff)


def days_since(timestamp: datetime, last_login: datetime | None) -> float:
    if last_login is None:
        return MAX_DAYS
    return min(MAX_DAYS, (timestamp - last_login).total_seconds() / 86400)
