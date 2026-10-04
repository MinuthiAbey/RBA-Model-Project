from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


@dataclass
class LoginEvent:
    user_id: str
    timestamp: datetime
    ip: str
    country: str | None = None
    asn: int | None = None
    user_agent: str | None = None
    browser: str | None = None
    os: str | None = None
    device_type: str | None = None
    rtt_ms: float | None = None
    success: bool | None = None  # outcome of the password check


@dataclass
class Reason:
    code: str
    text: str
    weight: float  # contribution to the score


@dataclass
class ScoreResult:
    raw: float  # the scorer's own scale, higher = riskier
    score: int  # calibrated 0-100
    reasons: list[Reason] = field(default_factory=list)  # largest contribution first


class Decision(Enum):
    ALLOW = "allow"
    OTP = "otp"
    BLOCK = "block"
