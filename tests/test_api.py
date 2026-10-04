import json
import threading
import urllib.request
from datetime import datetime
from http.server import ThreadingHTTPServer

import pytest

from engine.config import load_config
from engine.decision import Threshold, Thresholds
from engine.history import InMemoryHistory
from engine.scorers.rules import RuleScorer
from api.events import DEMO_AGENTS, build_event, describe_agent, locate
from api.seed import seed_history
from api.server import DemoEngine, make_handler

MAC, ANDROID = DEMO_AGENTS["mac_chrome"], DEMO_AGENTS["android_opera"]


@pytest.fixture
def engine():
    # Rule scorer with fixed thresholds, so each flow has a known outcome.
    history = InMemoryHistory()
    seed_history(history, datetime.now())
    thresholds = {"rules": {"0.1": Thresholds(otp=Threshold(25), block=Threshold(80)),
                            "0.2": Thresholds(otp=Threshold(5), block=Threshold(80))}}
    return DemoEngine({"rules": RuleScorer(load_config()["rules"])}, thresholds, "rules", "0.1", history, trust_forwarded=True)


def login(engine, ip, user_agent=MAC, username="alice"):
    return engine.score({"username": username, "forwarded_for": ip, "user_agent": user_agent})


def test_geo_lookup():
    assert locate("192.0.2.10") == ("NO", 29695)
    assert locate("198.51.100.7") == ("US", 393398)
    assert locate("8.8.8.8") == (None, None)
    assert locate("not an ip") == (None, None)


def test_dataset_user_agents_keep_dataset_labels():
    event = build_event("alice", "192.0.2.10", ANDROID, datetime.now(), success=True)
    assert (event.browser, event.os, event.device_type) == ("Opera Mobile 52.1.2254", "Android 13.0", "mobile")


def test_other_user_agents_are_parsed():
    iphone = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 "
              "(KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1")
    browser, os_name, device = describe_agent(iphone)
    assert device == "mobile" and os_name.startswith("iOS") and browser.startswith("Mobile Safari")


def test_seeded_accounts(engine):
    assert engine.history.get_user("alice").login_count == 20
    assert engine.history.get_user("bob").login_count == 5
    assert engine.history.get_user("charlie").login_count == 0


def test_usual_login_is_allowed(engine):
    result = login(engine, "192.0.2.10")
    assert result["decision"] == "allow" and result["context"]["prior_logins"] == 20


def test_new_country_asks_for_otp(engine):
    result = login(engine, "198.51.100.23")  # United States, same laptop
    assert result["decision"] == "otp"
    assert result["explanation"].startswith(f"Risk {result['score']}/100 (OTP): new country NO -> US")


def test_new_country_and_device_is_blocked(engine):
    assert login(engine, "198.51.100.23", ANDROID)["decision"] == "block"


def test_only_confirmed_logins_join_history(engine):
    result = login(engine, "198.51.100.23")
    assert engine.history.get_user("alice").login_count == 20
    engine.confirm({"event_id": result["event_id"]})
    assert engine.history.get_user("alice").login_count == 21
    assert engine.confirm({"event_id": result["event_id"]}) == {"confirmed": False}


def test_wrong_passwords_feed_failure_counter(engine):
    for _ in range(3):
        engine.record_failure({"username": "alice", "forwarded_for": "203.0.113.5"})
    assert engine.history.failures_last_hour("alice", datetime.now()) == 3


def test_forwarded_header_ignored_unless_trusted(engine):
    engine.trust_forwarded = False
    event = engine.event_from({"username": "alice", "forwarded_for": "198.51.100.23", "remote_addr": "127.0.0.1"}, True)
    assert event.ip == "127.0.0.1"


def test_http_round_trip(engine):
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(engine, {"scorer": "rules"}))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        request = urllib.request.Request(f"http://127.0.0.1:{server.server_port}/score", method="POST",
                                         data=json.dumps({"username": "alice", "forwarded_for": "192.0.2.10",
                                                          "user_agent": MAC}).encode())
        with urllib.request.urlopen(request) as response:
            assert json.load(response)["decision"] == "allow"
    finally:
        server.shutdown()


def lab_login(engine, **simulate):
    settings = {"country": "NO", "asn": 29695, "ip": "usual", "device": "mac_chrome", **simulate}
    return engine.score({"username": "alice", "simulate": settings})


def test_lab_usual_context_is_allowed(engine):
    engine.allow_simulated = True
    result = lab_login(engine)
    assert result["decision"] == "allow" and result["context"]["ip"] == "192.0.2.10"


def test_lab_changes_are_flagged(engine):
    engine.allow_simulated = True
    result = lab_login(engine, country="PL", asn=205727)
    assert result["decision"] == "otp"
    assert result["reasons"][0]["text"] == "new country NO -> PL"
    assert lab_login(engine, country="PL", asn=205727, device="android_opera")["decision"] == "block"


def test_lab_needs_the_config_flag(engine):
    engine.allow_simulated = False
    result = engine.score({"username": "alice", "simulate": {"country": "PL", "asn": 1, "ip": "new", "device": "mac_chrome"},
                           "forwarded_for": "192.0.2.10", "user_agent": MAC})
    assert result["context"]["country"] == "NO"


def test_clock_only_moves_forward(engine):
    first = engine.now()
    other_hour = (first.hour + 12) % 24
    later = engine.now(other_hour)
    assert later > first and later.hour == other_hour
    assert engine.now(first.hour) > later


def test_profiles_show_usual_context(engine):
    profiles = engine.profiles()
    assert profiles["alice"]["logins"] == 20
    assert profiles["alice"]["usual"]["country"] == "NO" and profiles["alice"]["usual"]["device"] == "mac_chrome"
    assert profiles["bob"]["usual"]["country"] == "GB"
    assert profiles["charlie"]["usual"] is None and profiles["charlie"]["logins"] == 0


def test_options_list_real_locations_and_devices(engine):
    options = engine.options()
    assert {"NO", "US", "PL"} <= {row["country"] for row in options["locations"]}
    assert "android_opera" in {row["key"] for row in options["devices"]}


def test_lab_budget_and_comparison(engine):
    engine.allow_simulated = True
    settings = {"country": "NO", "asn": 29695, "ip": "new", "device": "mac_chrome"}
    strict = engine.score({"username": "alice", "simulate": settings, "budget": 0.2, "compare": True})
    assert strict["budget"] == "0.2" and strict["decision"] == "otp"  # a new IP alone is challenged at the strict budget
    assert strict["comparison"] == [{"scorer": "rules", "score": 0, "decision": "otp", "trusted": False,
                                     "reason": "new IP address " + strict["context"]["ip"]}]
    unknown = engine.score({"username": "alice", "simulate": settings, "scorer": "nope", "budget": 0.99})
    assert (unknown["scorer"], unknown["budget"]) == ("rules", "0.1")


def test_a_verified_place_and_device_are_remembered(engine):
    # A strict threshold, so even a familiar country on a new IP still asks for a code unless it is remembered.
    engine.allow_simulated = True
    engine.thresholds["rules"]["0.1"] = Thresholds(otp=Threshold(5), block=Threshold(80))
    first = lab_login(engine, country="PL", asn=205727, ip="new")
    assert first["decision"] == "otp" and first["trusted_since"] is None
    engine.confirm({"event_id": first["event_id"], "verified": True})
    again = lab_login(engine, country="PL", asn=205727, ip="new")
    assert again["decision"] == "allow" and again["trusted_since"] is not None
    assert engine.profiles()["alice"]["trusted"][0]["country"] == "PL"
    elsewhere = lab_login(engine, country="PL", asn=49528, ip="new")  # same country, different network: not remembered
    assert elsewhere["decision"] == "otp"


def test_a_plain_allow_does_not_create_trust(engine):
    result = login(engine, "192.0.2.10")
    engine.confirm({"event_id": result["event_id"]})
    assert engine.profiles()["alice"]["trusted"] == []
