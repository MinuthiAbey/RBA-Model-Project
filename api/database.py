# SQLite storage for the platform: accounts and every sign-in event, so profiles survive restarts.

import hashlib
import hmac
import os
import sqlite3
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from engine.types import LoginEvent

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    username TEXT PRIMARY KEY,
    salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK (kind IN ('login', 'attempt', 'trust')),
    username TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    ip TEXT, country TEXT, asn INTEGER, user_agent TEXT, browser TEXT, os TEXT, device_type TEXT, success INTEGER
);
"""
EVENT_COLUMNS = "username, timestamp, ip, country, asn, user_agent, browser, os, device_type, success"


def hash_password(password: str, salt: bytes) -> str:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1).hex()


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.executescript(SCHEMA)

    def add_account(self, username: str, password: str, created_at: datetime) -> bool:
        salt = os.urandom(16)
        try:
            with self.conn:
                self.conn.execute("INSERT INTO accounts VALUES (?, ?, ?, ?)",
                                  (username, salt.hex(), hash_password(password, salt), created_at.isoformat()))
            return True
        except sqlite3.IntegrityError:
            return False  # the username is taken

    def check_password(self, username: str, password: str) -> bool:
        row = self.conn.execute("SELECT salt, password_hash FROM accounts WHERE username = ?", (username,)).fetchone()
        return row is not None and hmac.compare_digest(hash_password(password, bytes.fromhex(row[0])), row[1])

    def usernames(self) -> list[str]:
        return [row[0] for row in self.conn.execute("SELECT username FROM accounts ORDER BY rowid")]

    def record(self, kind: str, event: LoginEvent) -> None:
        values = (kind, event.user_id, event.timestamp.isoformat(), event.ip, event.country, event.asn, event.user_agent,
                  event.browser, event.os, event.device_type, None if event.success is None else int(event.success))
        with self.conn:
            self.conn.execute(f"INSERT INTO events (kind, {EVENT_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values)

    def events(self) -> Iterator[tuple[str, LoginEvent]]:
        for kind, user, ts, ip, country, asn, agent, browser, os_name, device, success in self.conn.execute(
                f"SELECT kind, {EVENT_COLUMNS} FROM events ORDER BY id"):
            yield kind, LoginEvent(user_id=user, timestamp=datetime.fromisoformat(ts), ip=ip, country=country, asn=asn,
                                   user_agent=agent, browser=browser, os=os_name, device_type=device,
                                   success=None if success is None else bool(success))
