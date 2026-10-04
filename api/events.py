# Turns a raw web login (IP + user-agent header) into the engine's LoginEvent.

import ipaddress
import json
from datetime import datetime
from pathlib import Path

from user_agents import parse

from engine.types import LoginEvent

HERE = Path(__file__).parent
# Offline demo map: documentation and private IP ranges -> a country and its most common network in the dataset.
GEO_RANGES = [(ipaddress.ip_network(row["range"]), row["country"], row["asn"])
              for row in json.loads((HERE / "geo_demo.json").read_text())]
# Real user-agent rows from the dataset with the dataset's own labels, so demo logins look like the data
# the models learned from. Any other browser is parsed normally.
DEVICES = json.loads((HERE / "ua_demo.json").read_text())
KNOWN_AGENTS = {row["user_agent"]: row for row in DEVICES.values()}
DEMO_AGENTS = {name: row["user_agent"] for name, row in DEVICES.items()}
# Countries the sign-in lab offers, each with its two most common real networks in the training data.
LOCATIONS = json.loads((HERE / "locations_demo.json").read_text())


def locate(ip: str) -> tuple[str | None, int | None]:
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return None, None
    for network, country, asn in GEO_RANGES:
        if address in network:
            return country, asn
    return None, None


def device_type(user_agent) -> str:
    if user_agent.is_bot:
        return "bot"
    if user_agent.is_tablet:
        return "tablet"
    if user_agent.is_mobile:
        return "mobile"
    return "desktop" if user_agent.is_pc else "unknown"


def describe_agent(user_agent: str | None) -> tuple[str, str, str]:
    if user_agent in KNOWN_AGENTS:
        known = KNOWN_AGENTS[user_agent]
        return known["browser"], known["os"], known["device_type"]
    parsed = parse(user_agent or "")
    return (f"{parsed.browser.family} {parsed.browser.version_string}".strip(),
            f"{parsed.os.family} {parsed.os.version_string}".strip(), device_type(parsed))


def device_name(user_agent: str | None) -> str | None:
    return next((name for name, row in DEVICES.items() if row["user_agent"] == user_agent), None)


def build_event(username: str, ip: str, user_agent: str | None, timestamp: datetime, success: bool,
                country: str | None = None, asn: int | None = None) -> LoginEvent:
    # The sign-in lab can state the country and network directly; otherwise they come from the IP.
    if country is None:
        country, asn = locate(ip)
    browser, os_name, device = describe_agent(user_agent)
    return LoginEvent(user_id=username, timestamp=timestamp, ip=ip, country=country, asn=asn,
                      user_agent=user_agent, browser=browser, os=os_name, device_type=device,
                      rtt_ms=None, success=success)
