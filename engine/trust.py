from datetime import datetime, timedelta

from engine.history import HistoryStore, trusted_key
from engine.types import Decision, LoginEvent

TRUST_DAYS = 30
MANY_ACCOUNTS_FROM_IP = 5


def trust_check(event: LoginEvent, history: HistoryStore) -> tuple[datetime | None, str | None]:
    """(when verified, None) if this exact country, network and device is trusted now;
    (None, why not) if it is remembered but paused; (None, None) if it was never verified."""
    verified = history.get_user(event.user_id).trusted.get(trusted_key(event))
    if verified is None:
        return None, None
    if event.timestamp - verified > timedelta(days=TRUST_DAYS):
        return None, f"it was verified more than {TRUST_DAYS} days ago"
    # Trust never applies while something else looks wrong right now.
    failures = history.failures_last_hour(event.user_id, event.timestamp)
    if failures:
        return None, f"{failures} wrong password{'s' if failures > 1 else ''} in the last hour"
    if history.ip_users_last_hour(event.ip, event.timestamp) >= MANY_ACCOUNTS_FROM_IP:
        return None, "this IP address tried many accounts in the last hour"
    return verified, None


def apply_trust(decision: Decision, event: LoginEvent, history: HistoryStore) -> tuple[Decision, datetime | None, str | None]:
    # Remember-this-device policy: a remembered context skips the one-time code. A block is never relaxed.
    if decision is not Decision.OTP:
        return decision, None, None
    since, paused = trust_check(event, history)
    return (Decision.ALLOW, since, None) if since else (decision, None, paused)
