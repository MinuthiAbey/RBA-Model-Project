import numpy as np
import pytest

from engine.calibration import Calibrator
from engine.decision import Threshold, Thresholds, choose_thresholds, decide, threshold_for_rate
from engine.explainer import explain
from engine.types import Decision, Reason, ScoreResult


def test_calibrated_scores_stay_in_range_and_are_monotonic():
    rng = np.random.default_rng(42)
    calibrator = Calibrator(rng.normal(size=1000))
    raws = np.sort(rng.normal(scale=3, size=5000))
    scores = calibrator.scores(raws)
    assert scores.min() >= 0 and scores.max() <= 100
    assert np.all(np.diff(scores) >= 0)


def test_calibrated_score_is_percentage_of_legit_below():
    calibrator = Calibrator(np.arange(1, 101))
    assert calibrator.score(50.5) == 50
    assert calibrator.score(0) == 0
    assert calibrator.score(1000) == 100


def test_decide_maps_thresholds():
    thresholds = Thresholds(otp=Threshold(0.5), block=Threshold(0.9))
    assert decide(0.1, thresholds) is Decision.ALLOW
    assert decide(0.6, thresholds) is Decision.OTP
    assert decide(0.95, thresholds) is Decision.BLOCK


def test_threshold_hits_target_rate_on_continuous_scores():
    legit = np.random.default_rng(1).random(10_000)
    thresholds = choose_thresholds(legit, challenge_rate=0.05, block_rate=0.005)
    assert thresholds.otp.expected_flags(legit).mean() == pytest.approx(0.05)
    assert thresholds.block.expected_flags(legit).mean() == pytest.approx(0.005)


def test_tied_scores_are_split_to_hit_the_budget():
    legit = np.array([0] * 80 + [10] * 10 + [100] * 10, dtype=float)
    threshold = threshold_for_rate(legit, 0.05)
    assert threshold == Threshold(100.0, 0.5)
    assert threshold.expected_flags(legit).mean() == pytest.approx(0.05)
    assert threshold.flags(100, draw=0.4) and not threshold.flags(100, draw=0.6)


def test_one_draw_keeps_blocks_inside_challenges():
    thresholds = Thresholds(otp=Threshold(100, 0.3), block=Threshold(100, 0.1))
    assert decide(100, thresholds, draw=lambda: 0.05) is Decision.BLOCK
    assert decide(100, thresholds, draw=lambda: 0.2) is Decision.OTP
    assert decide(100, thresholds, draw=lambda: 0.5) is Decision.ALLOW


def test_explain_line():
    result = ScoreResult(raw=0.8, score=82, reasons=[Reason("NEW_COUNTRY", "new country NO -> BR", 30),
                                                     Reason("NEW_DEVICE_TYPE", "new device type desktop -> mobile", 15)])
    assert explain(result, Decision.OTP) == \
        "Risk 82/100 (OTP): new country NO -> BR (+30), new device type desktop -> mobile (+15)"
