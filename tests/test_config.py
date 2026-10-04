"""Sanity checks on config.yaml, so a bad edit fails fast."""

from engine.config import load_config


def test_config_has_seed():
    assert load_config()["seed"] == 42


def test_splits_sum_to_one():
    splits = load_config()["splits"]
    assert abs(splits["train"] + splits["val"] + splits["test"] - 1.0) < 1e-9


def test_active_scorer_is_known():
    assert load_config()["demo"]["active_scorer"] in {"rules", "freeman", "iforest", "rforest"}
