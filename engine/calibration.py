import numpy as np


class Calibrator:
    """Turns a raw score into the percentage of legitimate validation logins it is riskier than (0-100)."""

    def __init__(self, legit_raw_scores) -> None:
        self.reference = np.sort(np.asarray(legit_raw_scores, dtype=float))
        if len(self.reference) == 0:
            raise ValueError("Calibration needs at least one legitimate score.")

    def scores(self, raw) -> np.ndarray:
        below = np.searchsorted(self.reference, np.asarray(raw, dtype=float), side="left")
        return (100 * below) // len(self.reference)

    def score(self, raw: float) -> int:
        return int(self.scores([raw])[0])
