from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from engine.calibration import Calibrator
from engine.history import HistoryStore
from engine.types import LoginEvent, Reason, ScoreResult


class Scorer:
    """Every scorer gives a raw score with reasons; calibration then maps it to 0-100."""

    name = "base"

    def __init__(self) -> None:
        self.calibrator: Calibrator | None = None

    def fit(self, features: pd.DataFrame, labels: np.ndarray | None = None) -> None:
        pass

    def raw_score(self, event: LoginEvent, history: HistoryStore) -> tuple[float, list[Reason]]:
        raise NotImplementedError

    def raw_scores(self, features: pd.DataFrame) -> np.ndarray:
        # Batch scoring from precomputed features; same numbers as raw_score, just faster.
        raise NotImplementedError

    def score(self, event: LoginEvent, history: HistoryStore) -> ScoreResult:
        raw, reasons = self.raw_score(event, history)
        calibrated = self.calibrator.score(raw) if self.calibrator else 0
        return ScoreResult(raw=raw, score=calibrated, reasons=reasons)

    def save(self, path: Path) -> None:
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: Path) -> "Scorer":
        return joblib.load(path)
