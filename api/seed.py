# Demo accounts and the login history they start with. This is demo data, never research data.

from datetime import datetime, timedelta

from engine.history import HistoryStore
from api.events import DEMO_AGENTS, build_event

# alice is a regular (Norway, Mac), bob is fairly new (UK, iPhone), charlie has never logged in (cold start).
ACCOUNTS = {
    "alice": {"logins": 20, "ip": "192.0.2.10", "user_agent": DEMO_AGENTS["mac_chrome"]},
    "bob": {"logins": 5, "ip": "172.16.4.20", "user_agent": DEMO_AGENTS["iphone_chrome"]},
    "charlie": {"logins": 0, "ip": "192.0.2.77", "user_agent": DEMO_AGENTS["mac_chrome"]},
}


def seed_history(history: HistoryStore, now: datetime) -> None:
    # One login a day at about the current time of day, so "now" always looks like a usual hour.
    for username, account in ACCOUNTS.items():
        for days_ago in range(account["logins"], 0, -1):
            when = now - timedelta(days=days_ago, minutes=(days_ago * 7) % 40 - 20)
            history.update(build_event(username, account["ip"], account["user_agent"], when, success=True))
