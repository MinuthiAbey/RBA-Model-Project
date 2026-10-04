import random
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from engine.types import Decision


@dataclass
class Threshold:
    value: float
    # Share of logins scoring exactly `value` that are flagged. Coarse scorers (e.g. the rules) put many
    # logins on one score, so flagging a random share of that tie is the only way to hit a budget exactly.
    tie_fraction: float = 1.0

    def flags(self, raw: float, draw: float) -> bool:
        return raw > self.value or (raw == self.value and draw < self.tie_fraction)

    def expected_flags(self, raw) -> np.ndarray:
        raw = np.asarray(raw, dtype=float)
        return np.where(raw > self.value, 1.0, np.where(raw == self.value, self.tie_fraction, 0.0))


@dataclass
class Thresholds:
    otp: Threshold
    block: Threshold


def decide(raw: float, thresholds: Thresholds, draw: Callable[[], float] = random.random) -> Decision:
    u = draw()  # one draw for both checks, so a blocked tie is always inside the challenged share
    if thresholds.block.flags(raw, u):
        return Decision.BLOCK
    if thresholds.otp.flags(raw, u):
        return Decision.OTP
    return Decision.ALLOW


def threshold_for_rate(legit_raw_scores, rate: float) -> Threshold:
    """Threshold that flags exactly `rate` of legitimate logins, splitting a tie at the cut-off if needed."""
    values, counts = np.unique(np.asarray(legit_raw_scores, dtype=float), return_counts=True)
    budget = rate * counts.sum()
    above = counts.sum() - np.cumsum(counts)  # logins scoring strictly higher than each value
    i = int(np.flatnonzero(above <= budget)[0])
    return Threshold(float(values[i]), float(min(1.0, (budget - above[i]) / counts[i])))


def choose_thresholds(legit_raw_scores, challenge_rate: float, block_rate: float) -> Thresholds:
    return Thresholds(otp=threshold_for_rate(legit_raw_scores, challenge_rate),
                      block=threshold_for_rate(legit_raw_scores, block_rate))


def thresholds_from_dict(saved: dict) -> Thresholds:
    return Thresholds(otp=Threshold(**saved["otp"]), block=Threshold(**saved["block"]))
