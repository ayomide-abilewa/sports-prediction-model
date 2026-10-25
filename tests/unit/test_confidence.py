from __future__ import annotations

from backend.betting.confidence import ConfidenceClassifier


def test_confidence_classifier_banker():
    classifier = ConfidenceClassifier(min_ev_threshold=0.02)
    # 80% prob at 1.30 odds -> EV = 80% * 1.30 - 1 = +4%
    res = classifier.evaluate(model_prob=0.80, available_odds=1.30, quality_score=1.0)
    assert res.is_value
    assert res.tier == "Tier 1 – Bankers"
    assert res.expected_value == 0.04


def test_confidence_classifier_negative_ev():
    classifier = ConfidenceClassifier(min_ev_threshold=0.025)
    # 60% prob at 1.40 odds -> EV = 0.60 * 1.40 - 1 = -16% (no value!)
    res = classifier.evaluate(model_prob=0.60, available_odds=1.40, quality_score=1.0)
    assert not res.is_value
    assert res.tier is None
    assert len(res.reasons) > 0


def test_confidence_classifier_sharp_value():
    classifier = ConfidenceClassifier(min_ev_threshold=0.02)
    # 52% prob at 2.10 odds -> EV = +9.2%
    res = classifier.evaluate(model_prob=0.52, available_odds=2.10, quality_score=0.9)
    assert res.is_value
    assert res.tier == "Tier 3 – Sharp Value"
