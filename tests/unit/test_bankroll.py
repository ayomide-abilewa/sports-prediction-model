from __future__ import annotations

from backend.betting.bankroll import BankrollEngine


def test_bankroll_quarter_kelly():
    engine = BankrollEngine(bankroll=1000.0, max_single_exposure_pct=0.05, kelly_fraction=0.25)
    # 55% prob at 2.00 odds -> full Kelly = (0.55*1 - 0.45)/1 = 10%
    # Quarter Kelly = 2.5% of 1000 = $25.00
    rec = engine.calculate_kelly_stake(model_prob=0.55, decimal_odds=2.00)
    assert rec.stake_amount == 25.0
    assert rec.stake_percentage == 0.025
    assert rec.bankroll_remaining == 975.0
    assert rec.warning is None


def test_bankroll_kelly_negative_ev():
    engine = BankrollEngine(bankroll=1000.0)
    # 40% prob at 2.00 odds -> negative EV
    rec = engine.calculate_kelly_stake(model_prob=0.40, decimal_odds=2.00)
    assert rec.stake_amount == 0.0
    assert "Negative expected value" in (rec.warning or "")


def test_bankroll_kelly_capped_at_max():
    engine = BankrollEngine(bankroll=1000.0, max_single_exposure_pct=0.05, kelly_fraction=1.0)
    # 80% prob at 2.00 odds -> full Kelly = (0.80*1 - 0.20)/1 = 60%!
    # Should cap strictly at 5% = $50
    rec = engine.calculate_kelly_stake(model_prob=0.80, decimal_odds=2.00)
    assert rec.stake_amount == 50.0
    assert rec.stake_percentage == 0.05
    assert "capped" in (rec.warning or "")
