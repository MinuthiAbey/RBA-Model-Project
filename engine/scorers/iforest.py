import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from engine.explainer import describe
from engine.features import FEATURES, extract
from engine.history import HistoryStore
from engine.scorers.base import Scorer
from engine.types import LoginEvent, Reason

# For these features a lower value is the unusual one; for all others a higher value is.
LOWER_IS_RISKIER = {"prior_logins"}
MIN_Z = 1.0  # only call a feature a reason if it is at least one standard deviation from normal


class IsolationForestScorer(Scorer):
    """Unsupervised: learns what normal logins look like and scores how easy a login is to isolate."""

    name = "iforest"

    def __init__(self, n_estimators: int, seed: int) -> None:
        super().__init__()
        self.model = IsolationForest(n_estimators=n_estimators, random_state=seed, n_jobs=-1)

    def fit(self, features: pd.DataFrame, labels: np.ndarray | None = None) -> None:
        legit = features[FEATURES]
        self.model.fit(legit.to_numpy())
        self.model.set_params(n_jobs=1)  # single logins are scored faster without thread start-up
        self.mean = legit.mean()
        self.std = legit.std().replace(0, 1)

    def raw_scores(self, features: pd.DataFrame) -> np.ndarray:
        return -self.model.score_samples(features[FEATURES].to_numpy())

    def raw_score(self, event: LoginEvent, history: HistoryStore) -> tuple[float, list[Reason]]:
        features = extract(event, history)
        raw = float(self.raw_scores(pd.DataFrame([features]))[0])
        # Reasons: the three features furthest from normal, measured in standard deviations.
        z = (pd.Series(features) - self.mean) / self.std
        z[list(LOWER_IS_RISKIER)] *= -1
        user = history.get_user(event.user_id)
        reasons = [Reason(name.upper(), describe(name, event, user, features), float(z[name]))
                   for name in z.nlargest(3).index if z[name] >= MIN_Z]
        return raw, reasons
