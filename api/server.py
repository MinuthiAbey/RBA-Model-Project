# Local scoring API for the LightRBA web app. It holds the login history in memory and binds to 127.0.0.1 only.

import json
import random
import re
import threading
import time
import uuid
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import joblib

from engine.config import PROJECT_ROOT, configured_path, load_config
from engine.decision import Threshold, Thresholds, decide, thresholds_from_dict
from engine.explainer import explain
from engine.features import typical_hour
from engine.history import HistoryStore, InMemoryHistory
from engine.scorers.base import Scorer
from engine.trust import apply_trust
from engine.types import LoginEvent
from api.database import Database
from api.events import DEVICES, LOCATIONS, build_event, device_name
from api.seed import ACCOUNTS, seed_database

MODELS = PROJECT_ROOT / "models"
USERNAME = re.compile(r"^[a-z0-9_]{3,20}$")
MIN_PASSWORD = 8


class DemoEngine:
    def __init__(self, scorers: dict[str, Scorer], thresholds: dict[str, dict[str, Thresholds]], default_scorer: str,
                 default_budget: str, history: HistoryStore, trust_forwarded: bool, allow_simulated: bool = False,
                 database: Database | None = None) -> None:
        self.scorers = scorers
        self.thresholds = thresholds  # scorer -> challenge budget -> thresholds, all chosen on the validation period
        self.default_scorer = default_scorer
        self.default_budget = default_budget
        self.history = history
        self.trust_forwarded = trust_forwarded
        self.allow_simulated = allow_simulated
        self.pending: dict[str, LoginEvent] = {}  # scored logins waiting for allow/OTP success
        self.clock = datetime.now()
        self.lock = threading.Lock()
        self.database = database
        if database:
            self.replay(database)

    def replay(self, database: Database) -> None:
        # Rebuild the in-memory history from every stored event, in the order they happened.
        for kind, event in database.events():
            if kind == "login":
                self.history.update(event)
            elif kind == "attempt":
                self.history.record_attempt(event)
            else:
                self.history.trust(event)
            self.clock = max(self.clock, event.timestamp)

    def save(self, kind: str, event: LoginEvent) -> None:
        if self.database:
            self.database.record(kind, event)

    @classmethod
    def from_models(cls, config: dict) -> "DemoEngine":
        saved = json.loads((MODELS / "thresholds.json").read_text())
        scorers = {name: Scorer.load(MODELS / f"{name}.joblib") for name in saved}
        # The OTP threshold comes from the research operating point for each budget; blocking always keeps 0.5%.
        thresholds = {name: {budget: Thresholds(otp=Threshold(**point), block=thresholds_from_dict(saved[name]).block)
                             for budget, point in saved[name]["operating_points"].items()}
                      for name in saved}
        history = InMemoryHistory(joblib.load(MODELS / "global_freqs.joblib"))
        database = Database(configured_path("database"))
        if not database.usernames():
            seed_database(database, datetime.now())
        return cls(scorers, thresholds, config["demo"]["active_scorer"], str(config["demo"]["challenge_budget"]), history,
                   config["demo"]["trust_forwarded_headers"], config["demo"]["allow_simulated_context"], database)

    def now(self, hour: int | None = None) -> datetime:
        # The demo clock only moves forward, so the history stays in time order even when the lab
        # asks for another time of day (that jumps ahead to the next time the clock shows that hour).
        current = max(datetime.now(), self.clock)
        if hour is not None and hour != current.hour:
            target = current.replace(hour=hour, minute=5, second=0, microsecond=0)
            current = target if target > current else target + timedelta(days=1)
        self.clock = current
        return current

    def event_from(self, body: dict, success: bool) -> LoginEvent:
        simulated = body.get("simulate")
        if simulated and self.allow_simulated:
            return self.simulated_event(body["username"], simulated, success)
        forwarded = (body.get("forwarded_for") or "").split(",")[0].strip()
        ip = forwarded if self.trust_forwarded and forwarded else body.get("remote_addr") or "127.0.0.1"
        return build_event(body["username"], ip, body.get("user_agent"), self.now(), success)

    def simulated_event(self, username: str, simulated: dict, success: bool) -> LoginEvent:
        # Sign-in lab only (LOCAL DEMO): the presenter picks the country, network, IP, device and time of day.
        user = self.history.get_user(username)
        usual_ip = user.most_common("ip")
        ip = usual_ip if simulated.get("ip") == "usual" and usual_ip else f"100.{random.randint(64, 127)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        device = DEVICES[simulated["device"]]
        hour = simulated.get("hour")
        return build_event(username, ip, device["user_agent"], self.now(None if hour is None else int(hour) % 24),
                           success, country=str(simulated["country"]), asn=int(simulated["asn"]))

    def settings(self, body: dict) -> tuple[str, str]:
        # The lab may pick another model or budget; anything unknown falls back to the configured ones.
        name = body.get("scorer") if body.get("scorer") in self.scorers else self.default_scorer
        budget = str(body.get("budget")) if str(body.get("budget")) in self.thresholds[name] else self.default_budget
        return name, budget

    def score(self, body: dict) -> dict:
        event = self.event_from(body, success=True)
        prior_logins = self.history.get_user(event.user_id).login_count
        name, budget = self.settings(body)
        draw = random.random()  # one draw, so every model splits ties at its threshold the same way
        started = time.perf_counter()
        result = self.scorers[name].score(event, self.history)
        decision = decide(result.raw, self.thresholds[name][budget], draw=lambda: draw)
        decision, trusted, trust_paused = apply_trust(decision, event, self.history)
        elapsed_ms = (time.perf_counter() - started) * 1000
        comparison = self.compare(event, budget, draw) if body.get("compare") else None
        self.history.record_attempt(event)
        self.save("attempt", event)
        event_id = uuid.uuid4().hex
        self.pending[event_id] = event
        return {
            "event_id": event_id,
            "scorer": name,
            "budget": budget,
            "decision": decision.value,
            "score": result.score,
            "reasons": [{"code": r.code, "text": r.text, "weight": r.weight} for r in result.reasons],
            "explanation": explain(result, decision) + (f" · remembered device and place, verified {trusted:%d %b %H:%M}" if trusted else ""),
            "trusted_since": trusted.isoformat() if trusted else None,
            "trust_paused": trust_paused,
            "scoring_ms": round(elapsed_ms, 2),
            "context": context(event, prior_logins),
            "comparison": comparison,
        }

    def compare(self, event: LoginEvent, budget: str, draw: float) -> list[dict]:
        # The same sign-in through every model at the same challenge budget (before the history learns from it).
        rows = []
        for name, scorer in self.scorers.items():
            result = scorer.score(event, self.history)
            thresholds = self.thresholds[name].get(budget)
            if thresholds is None:
                continue
            decision, trusted, _ = apply_trust(decide(result.raw, thresholds, draw=lambda: draw), event, self.history)
            rows.append({"scorer": name, "score": result.score, "decision": decision.value, "trusted": trusted is not None,
                         "reason": result.reasons[0].text if result.reasons else None})
        return rows

    def record_failure(self, body: dict) -> dict:
        # Wrong passwords are never scored, but they feed the failure and IP-velocity counters.
        event = self.event_from(body, success=False)
        prior_logins = self.history.get_user(event.user_id).login_count
        self.history.record_attempt(event)
        self.save("attempt", event)
        return {"context": context(event, prior_logins)}

    def confirm(self, body: dict) -> dict:
        # Only a login that was allowed, or passed the OTP check, becomes part of the user's history.
        # Passing the one-time code also makes this place and device trusted for a while (engine/trust.py).
        event = self.pending.pop(body["event_id"], None)
        if event:
            self.history.update(event)
            self.save("login", event)
            if body.get("verified"):
                self.history.trust(event)
                self.save("trust", event)
        return {"confirmed": event is not None}

    def discard(self, body: dict) -> dict:
        return {"discarded": self.pending.pop(body["event_id"], None) is not None}

    def check_password(self, body: dict) -> dict:
        return {"ok": bool(self.database) and self.database.check_password(body["username"], body["password"])}

    def register(self, body: dict) -> dict:
        # A new account; its sign-up conditions become its first known sign-in.
        username, password = body["username"], body["password"]
        if not USERNAME.match(username):
            return {"created": False, "error": "Use 3–20 lowercase letters, digits or underscores."}
        if len(password) < MIN_PASSWORD:
            return {"created": False, "error": f"Use a password of at least {MIN_PASSWORD} characters."}
        event = self.event_from(body, success=True)
        if not self.database or not self.database.add_account(username, password, event.timestamp):
            return {"created": False, "error": "That username is taken."}
        self.history.update(event)
        self.save("login", event)
        return {"created": True, "context": context(event, 0)}

    def profiles(self) -> dict:
        # What each user's normal sign-in looks like, straight from the history the engine has learned.
        result = {}
        for username in self.database.usernames() if self.database else ACCOUNTS:
            user = self.history.get_user(username)
            hour = typical_hour(user.hour_counts)
            usual = None
            if user.login_count:
                usual = {"country": user.most_common("country"), "asn": user.most_common("asn"),
                         "ip": user.most_common("ip"), "device": device_name(user.most_common("user_agent")),
                         "browser": user.most_common("browser"), "os": user.most_common("os"),
                         "device_type": user.most_common("device_type"), "hour": None if hour is None else int(hour) % 24}
            result[username] = {
                "logins": user.login_count,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "usual": usual,
                "seen_countries": sorted(c for c in user.seen["country"] if c),
                "seen_devices": sorted(d for d in user.seen["device_type"] if d),
                "trusted": [{"country": country, "asn": asn, "device": device_name(agent), "since": since.isoformat()}
                            for (country, asn, agent), since in user.trusted.items()],
            }
        return result

    def options(self) -> dict:
        return {"locations": LOCATIONS,
                "devices": [{"key": key, "label": row["label"], "device_type": row["device_type"]} for key, row in DEVICES.items()],
                "scorers": list(self.scorers),
                "budgets": sorted(self.thresholds[self.default_scorer], key=float)}


def context(event: LoginEvent, prior_logins: int) -> dict:
    return {"ip": event.ip, "country": event.country, "asn": event.asn, "browser": event.browser,
            "os": event.os, "device_type": event.device_type, "prior_logins": prior_logins,
            "time": event.timestamp.isoformat()}


def make_handler(engine: DemoEngine, info: dict):
    posts = {"/score": engine.score, "/failed": engine.record_failure, "/confirm": engine.confirm,
             "/discard": engine.discard, "/accounts/check": engine.check_password, "/accounts/register": engine.register}
    gets = {"/info": lambda: info, "/profiles": engine.profiles, "/options": engine.options}

    class Handler(BaseHTTPRequestHandler):
        def send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            route = gets.get(self.path)
            if route is None:
                self.send_json(404, {"error": "not found"})
                return
            with engine.lock:
                self.send_json(200, route())

        def do_POST(self) -> None:
            route = posts.get(self.path)
            if route is None:
                self.send_json(404, {"error": "not found"})
                return
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                with engine.lock:
                    self.send_json(200, route(body))
            except (KeyError, ValueError, TypeError) as error:
                self.send_json(400, {"error": str(error)})

        def log_message(self, *args) -> None:
            pass  # keep the console for the decisions printed by the web app

    return Handler


def main() -> None:
    config = load_config()
    engine = DemoEngine.from_models(config)
    port = config["demo"]["engine_port"]
    info = {"scorer": engine.default_scorer, "challenge_budget": float(engine.default_budget)}
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(engine, info))
    print(f"Risk engine ({config['demo']['active_scorer']}) listening on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
