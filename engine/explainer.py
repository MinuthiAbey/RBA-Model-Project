from engine.history import UserHistory
from engine.types import Decision, LoginEvent, ScoreResult


def explain(result: ScoreResult, decision: Decision, top_n: int = 3) -> str:
    """One line such as: Risk 82/100 (OTP): new country NO -> BR (+30), new device type mobile (+15)"""
    line = f"Risk {result.score}/100 ({decision.name})"
    reasons = ", ".join(f"{r.text} (+{format_weight(r.weight)})" for r in result.reasons[:top_n])
    return f"{line}: {reasons}" if reasons else line


def format_weight(weight: float) -> str:
    return str(int(weight)) if float(weight).is_integer() else f"{weight:.2f}"


def describe(name: str, event: LoginEvent, user: UserHistory, features: dict[str, float]) -> str:
    """Plain-English text for a feature or context field that pushed the score up."""
    match name:
        case "prior_logins":
            return f"short login history ({int(features['prior_logins'])} previous logins)"
        case "new_ip" | "ip":
            return f"new IP address {event.ip}"
        case "new_asn" | "asn":
            return f"new network AS{event.asn}"
        case "new_country" | "country":
            usual = user.most_common("country")
            return f"new country {usual} -> {event.country}" if usual else f"new country {event.country}"
        case "user_agent":
            return "new browser fingerprint"
        case "new_browser" | "browser":
            return f"new browser {event.browser}"
        case "new_os" | "os":
            return f"new operating system {event.os}"
        case "new_device_type" | "device_type":
            usual = user.most_common("device_type")
            if usual:
                return f"new device type {usual} -> {event.device_type}"
            return f"new device type {event.device_type}"
        case "hour_deviation":
            return f"unusual hour {event.timestamp:%H:%M}"
        case "days_since_last_login":
            days = features["days_since_last_login"]
            return "no previous login" if user.login_count == 0 else f"{days:.0f} days since last login"
        case "user_failures_1h":
            return f"{int(features['user_failures_1h'])} failed attempts in the last hour"
        case "ip_distinct_users_1h":
            return f"IP tried {int(features['ip_distinct_users_1h'])} accounts in the last hour"
        case "asn_global_rarity":
            return f"rarely seen network AS{event.asn}"
        case "country_global_rarity":
            return f"rarely seen country {event.country}"
        case "ua_global_rarity":
            return f"rarely seen browser/OS ({event.browser} on {event.os})"
        case "rtt_missing" | "rtt_ms":
            return "unusual network round-trip time"
    return name.replace("_", " ")
