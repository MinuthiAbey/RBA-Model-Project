import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from engine.explainer import describe
from engine.features import FEATURES, extract
from engine.history import HistoryStore
from engine.scorers.base import Scorer
from engine.types import LoginEvent, Reason

MIN_CONTRIBUTION = 0.01  # smaller changes in P(attack) are noise, not reasons


class RandomForestScorer(Scorer):
    """Supervised: learns from real legitimate logins and real attacker-IP attempts; raw score = P(attack)."""

    name = "rforest"

    def __init__(self, n_estimators: int, class_weight: str, min_samples_leaf: int, seed: int) -> None:
        super().__init__()
        self.model = RandomForestClassifier(n_estimators=n_estimators, class_weight=class_weight,
                                            min_samples_leaf=min_samples_leaf, random_state=seed, n_jobs=-1)

    def fit(self, features: pd.DataFrame, labels: np.ndarray | None = None) -> None:
        self.model.fit(features[FEATURES].to_numpy(), labels)
        self.model.set_params(n_jobs=1)  # single logins are scored faster without thread start-up
        self.legit_median = features.loc[labels == 0, FEATURES].median()

    def raw_scores(self, features: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(features[FEATURES].to_numpy())[:, 1]

    def raw_score(self, event: LoginEvent, history: HistoryStore) -> tuple[float, list[Reason]]:
        features = extract(event, history)
        # Reasons: how much P(attack) drops when one feature is set to a typical legitimate value.
        rows = pd.DataFrame([features] * (len(FEATURES) + 1))
        for i, name in enumerate(FEATURES, start=1):
            rows.loc[i, name] = self.legit_median[name]
        probs = self.raw_scores(rows)
        raw = float(probs[0])
        user = history.get_user(event.user_id)
        contributions = sorted(zip(FEATURES, raw - probs[1:]), key=lambda item: item[1], reverse=True)
        reasons = [Reason(name.upper(), describe(name, event, user, features), float(delta))
                   for name, delta in contributions[:3] if delta >= MIN_CONTRIBUTION]
        return raw, reasons
