# Credential-stuffing simulator for the local LightRBA platform. It refuses to target anything but this machine.

import argparse
import random
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import requests

ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
CREDS = Path(__file__).with_name("creds_demo.txt")
# A handful of attacker addresses from the documentation ranges (mapped to US and DE by the demo's geo table).
ATTACK_IPS = ["198.51.100.66", "198.51.100.67", "198.51.100.68", "203.0.113.66", "203.0.113.67"]
USER_AGENTS = [
    "Mozilla/5.0 (Linux; U; Android 13.0; i phone X Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Version/4.0 Chrome/85.0.4183.127 Mobile Safari/537.36 OPR/52.1.2254.54298",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "python-requests/2.31.0",
]
OUTCOMES = {"/account": "SIGNED IN", "/verify": "OTP challenge"}


def check_target(url: str) -> None:
    host = urlparse(url).hostname
    if host not in ALLOWED_HOSTS:
        raise SystemExit(f"Refusing to attack {host!r}: this simulator only targets 127.0.0.1 or localhost.")


def load_credentials(path: Path) -> list[tuple[str, str]]:
    lines = [line.strip() for line in path.read_text().splitlines() if line.strip() and not line.startswith("#")]
    return [tuple(line.split(":", 1)) for line in lines]


def attempt(target: str, username: str, password: str, ip: str, user_agent: str, rng: random.Random) -> str:
    session = requests.Session()
    headers = {"X-Forwarded-For": ip, "User-Agent": user_agent, "Origin": target}
    response = session.post(f"{target}/api/login", json={"username": username, "password": password},
                            headers=headers, timeout=10)
    if not response.ok:
        return {401: "wrong password", 403: "BLOCKED", 503: "engine unavailable"}.get(response.status_code,
                                                                                       str(response.status_code))
    outcome = OUTCOMES.get(response.json().get("next"), "unknown")
    if outcome == "OTP challenge":
        # The attacker has the password but not the one-time code, so all they can do is guess.
        for _ in range(3):
            guess = f"{rng.randrange(1_000_000):06d}"
            response = session.post(f"{target}/api/verify", json={"code": guess}, headers=headers, timeout=10)
            if response.ok:
                return "SIGNED IN (guessed the code)"
            if response.status_code != 401:  # 401 = wrong code, try again; anything else ends the attempt
                break
        if response.status_code == 403:
            return "OTP challenge -> BLOCKED after 3 wrong codes"
        return f"OTP challenge -> stopped ({response.json().get('error', response.status_code)})"
    return outcome


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__ or "Credential-stuffing simulator (localhost only)")
    parser.add_argument("--target", default="http://127.0.0.1:3000")
    parser.add_argument("--creds", type=Path, default=CREDS)
    parser.add_argument("--attempts", type=int, default=None, help="default: every line in the creds file")
    parser.add_argument("--rate", type=float, default=4.0, help="attempts per second")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    check_target(args.target)
    rng = random.Random(args.seed)
    credentials = load_credentials(args.creds)[: args.attempts]
    summary = Counter()
    print(f"Credential stuffing against {args.target}: {len(credentials)} attempts at {args.rate}/s")
    for i, (username, password) in enumerate(credentials):
        ip = ATTACK_IPS[i % len(ATTACK_IPS)]
        outcome = attempt(args.target, username, password, ip, rng.choice(USER_AGENTS), rng)
        summary[outcome] += 1
        print(f"  {i + 1:3}. {username:>10} from {ip:<14} -> {outcome}")
        time.sleep(1 / args.rate)

    print("\nSummary: " + ", ".join(f"{outcome}: {n}" for outcome, n in summary.most_common()))
    if any(outcome.startswith("SIGNED IN") for outcome in summary):
        print("Warning: at least one attacker got in.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
