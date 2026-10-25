from __future__ import annotations

import numpy as np
from backend.probability.calibration import ProbabilityCalibrator
from backend.probability.markets import MarketEngine


def test_market_engine_fair_odds():
    assert MarketEngine.calculate_fair_odds(0.50) == 2.00
    assert MarketEngine.calculate_fair_odds(0.25) == 4.00
    assert MarketEngine.calculate_fair_odds(0.80) == 1.25


def test_market_engine_remove_margin():
    # Decimal odds with ~5% bookmaker overround
    # Implied: 1/2.0 = 0.50, 1/3.4 = 0.294, 1/3.8 = 0.263 -> sum = 1.057
    odds = {"home": 2.0, "draw": 3.4, "away": 3.8}
    probs = MarketEngine.remove_bookmaker_margin(odds)

    total_prob = sum(probs.values())
    assert np.isclose(total_prob, 1.0, atol=1e-2)
    assert probs["home"] < 0.50  # Overround removed reduces raw implied


def test_market_engine_expected_value():
    # 55% model probability at 2.00 odds -> EV = (0.55 * 2.00) - 1 = +0.10 (+10%)
    ev = MarketEngine.calculate_expected_value(0.55, 2.00)
    assert ev == 0.10

    # 40% model probability at 2.00 odds -> EV = (0.40 * 2.00) - 1 = -0.20 (-20%)
    ev_neg = MarketEngine.calculate_expected_value(0.40, 2.00)
    assert ev_neg == -0.20


def test_probability_calibrator_isotonic():
    np.random.seed(42)
    # Generate uncalibrated probabilities that are overconfident
    raw = np.linspace(0.1, 0.9, 100)
    outcomes = (np.random.rand(100) < (raw * 0.8)).astype(int)

    calibrator = ProbabilityCalibrator(method="isotonic")
    calibrator.fit(raw, outcomes)

    calibrated = calibrator.calibrate(np.array([0.5, 0.8]))
    assert len(calibrated) == 2
    assert 0.0 < calibrated[0] < 1.0
    assert 0.0 < calibrated[1] < 1.0

    eval_res = calibrator.evaluate_calibration(raw, outcomes)
    assert "brier_score" in eval_res
    assert "log_loss" in eval_res
    assert "ece" in eval_res
