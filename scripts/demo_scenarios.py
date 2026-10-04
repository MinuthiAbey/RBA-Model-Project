# Runs the four presentation scenarios against the local DemoShop, pausing so the presenter can talk.

import argparse
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from attack import stuffing  # noqa: E402
from api.events import DEMO_AGENTS  # noqa: E402

TARGET = "http://127.0.0.1:3000"


def sign_in(username: str, ip: str, agent: str, password: str = "demo1234") -> tuple[requests.Session, dict]:
    session = requests.Session()
    response = session.post(f"{TARGET}/api/login", json={"username": username, "password": password},
                            headers={"X-Forwarded-For": ip, "User-Agent": DEMO_AGENTS[agent], "Origin": TARGET})
    latest = requests.get(f"{TARGET}/api/events").json()["records"][0]
    print(f"   {username} from {ip} ({latest['country']}), {latest['device']}")
    print(f"   -> {latest['outcome'].upper()}  {latest['explanation']}")
    return session, response.json()


def pass_otp(session: requests.Session) -> None:
    code = requests.get(f"{TARGET}/api/events").json()["latestOtp"]["code"]
    response = session.post(f"{TARGET}/api/verify", json={"code": code}, headers={"Origin": TARGET})
    print(f"   entered the one-time code {code} -> {'signed in' if response.ok else response.json().get('error')}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-pause", action="store_true", help="run straight through (for testing)")
    args = parser.parse_args()
    pause = (lambda: None) if args.no_pause else (lambda: input("\n   [Enter] for the next scenario "))

    print("\n1. Normal login: alice, from home in Norway on her usual Mac")
    sign_in("alice", "192.0.2.10", "mac_chrome")
    pause()

    print("\n2. Suspicious login: alice's correct password, but from the US on an Android phone")
    session, reply = sign_in("alice", "198.51.100.23", "android_opera")
    if reply.get("next") == "/verify":
        pass_otp(session)
    pause()

    print("\n3. New user (cold start): charlie has never logged in")
    print("   a) first ever login, from the US on an Android phone")
    sign_in("charlie", "198.51.100.77", "android_opera")
    print("   b) first ever login, from Norway on a Mac")
    sign_in("charlie", "192.0.2.77", "mac_chrome")
    pause()

    print("\n4. Credential stuffing: leaked passwords tried from a few attacker IPs")
    return stuffing.main(["--target", TARGET, "--rate", "4"])


if __name__ == "__main__":
    sys.exit(main())
