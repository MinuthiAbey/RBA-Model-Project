import numpy as np
import pandas as pd

from engine.explainer import describe
from engine.features import extract
from engine.history import HistoryStore
from engine.scorers.base import Scorer
from engine.types import LoginEvent, Reason

# (weight name in config.yaml, feature, the rule fires when feature >= this value)
RULES = [
    ("new_country", "new_country", 1),
    ("new_asn", "new_asn", 1),
    ("new_ip", "new_ip", 1),
    ("new_device_type", "new_device_type", 1),
    ("new_browser", "new_browser", 1),
    ("new_os", "new_os", 1),
    ("unusual_hour", "hour_deviation", 6),
    ("user_failures_1h_ge_3", "user_failures_1h", 3),
    ("ip_distinct_users_1h_ge_5", "ip_distinct_users_1h", 5),
]
MAX_SCORE = 100.0


class RuleScorer(Scorer):
    """Fixed points per warning sign, capped at 100. Weights are set in advance, never tuned on data."""

    name = "rules"

    def __init__(self, weights: dict[str, float]) -> None:
        super().__init__()
        self.weights = dict(weights)

    def raw_score(self, event: LoginEvent, history: HistoryStore) -> tuple[float, list[Reason]]:
        features = extract(event, history)
        user = history.get_user(event.user_id)
        reasons = [Reason(feature.upper(), describe(feature, event, user, features), self.weights[key])
                   for key, feature, fires_at in RULES if features[feature] >= fires_at]
        reasons.sort(key=lambda r: r.weight, reverse=True)
        return min(MAX_SCORE, sum(r.weight for r in reasons)), reasons

    def raw_scores(self, features: pd.DataFrame) -> np.ndarray:
        total = np.zeros(len(features))
        for key, feature, fires_at in RULES:
            total += self.weights[key] * (features[feature].to_numpy() >= fires_at)
        return np.minimum(total, MAX_SCORE)
