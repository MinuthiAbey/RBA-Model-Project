# Demo accounts and the sign-in history they start with. This is demo data, never research data.

from collections.abc import Iterator
from datetime import datetime, timedelta

from api.events import DEMO_AGENTS, build_event
from engine.history import HistoryStore
from engine.types import LoginEvent

DEMO_PASSWORD = "demo1234"

# Each person signs in once a day around their own hour, from one place on one device.
# charlie has never signed in: the cold-start case.
ACCOUNTS = {
    "alice":   {"logins": 20, "hour": 9,  "country": "NO", "asn": 29695,  "ip": "192.0.2.10",   "device": "mac_chrome"},
    "bob":     {"logins": 5,  "hour": 13, "country": "GB", "asn": 29550,  "ip": "172.16.4.20",  "device": "iphone_chrome"},
    "charlie": {"logins": 0,  "hour": 10, "country": "NO", "asn": 29695,  "ip": "192.0.2.77",   "device": "mac_chrome"},
    "diana":   {"logins": 12, "hour": 18, "country": "US", "asn": 393398, "ip": "198.51.100.12", "device": "windows_chrome"},
    "erik":    {"logins": 40, "hour": 21, "country": "NO", "asn": 41164,  "ip": "10.20.30.40",  "device": "android_opera"},
    "fatima":  {"logins": 8,  "hour": 8,  "country": "DE", "asn": 9063,   "ip": "203.0.113.8",  "device": "mac_chrome"},
    "george":  {"logins": 3,  "hour": 11, "country": "AU", "asn": 60117,  "ip": "100.70.1.3",   "device": "iphone_chrome"},
    "hana":    {"logins": 15, "hour": 15, "country": "PL", "asn": 205727, "ip": "100.80.2.15",  "device": "android_tablet"},
    "ivan":    {"logins": 25, "hour": 23, "country": "UA", "asn": 43309,  "ip": "100.90.3.25",  "device": "windows_chrome"},
    "jun":     {"logins": 6,  "hour": 7,  "country": "IN", "asn": 45775,  "ip": "100.100.4.6", "device": "android_opera"},
}


def seed_events(now: datetime) -> Iterator[LoginEvent]:
    for username, account in ACCOUNTS.items():
        for days_ago in range(account["logins"], 0, -1):
            day = now - timedelta(days=days_ago)
            when = day.replace(hour=account["hour"], minute=(days_ago * 7) % 50, second=0, microsecond=0)
            yield build_event(username, account["ip"], DEMO_AGENTS[account["device"]], when, success=True,
                              country=account["country"], asn=account["asn"])


def seed_history(history: HistoryStore, now: datetime) -> None:
    for event in seed_events(now):
        history.update(event)


def seed_database(database, now: datetime) -> None:
    # Only for an empty database: create the demo accounts and store their past sign-ins.
    for username, account in ACCOUNTS.items():
        database.add_account(username, DEMO_PASSWORD, now - timedelta(days=account["logins"] + 1))
    for event in seed_events(now):
        database.record("login", event)
