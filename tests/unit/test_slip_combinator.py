from __future__ import annotations

from backend.betting.slip_combinator import CandidateLeg, SlipCombinator


def test_slip_combinator_banker_rollover():
    candidates = [
        CandidateLeg(
            prediction_id=1, match_id=101, league_code="ENG-Premier League",
            home_team="Arsenal", away_team="Chelsea", market_type="1x2", selection="home",
            odds=1.45, probability=0.75, expected_value=0.08,
        ),
        CandidateLeg(
            prediction_id=2, match_id=102, league_code="ESP-La Liga",
            home_team="Real Madrid", away_team="Getafe", market_type="1x2", selection="home",
            odds=1.50, probability=0.72, expected_value=0.08,
        ),
        CandidateLeg(
            prediction_id=3, match_id=103, league_code="ITA-Serie A",
            home_team="Inter", away_team="Monza", market_type="over_under_2.5", selection="over",
            odds=1.40, probability=0.78, expected_value=0.09,
        ),
    ]

    slips = SlipCombinator.generate_slips(candidates, category="banker_rollover", max_results=3)
    assert len(slips) > 0
    slip = slips[0]
    assert 1.80 <= slip.combined_odds <= 2.60
    assert 2 <= len(slip.legs) <= 3
    assert slip.joint_probability > 0.0


def test_slip_combinator_rejects_duplicate_matches():
    # Two legs from the exact same match ID 999
    candidates = [
        CandidateLeg(
            prediction_id=1, match_id=999, league_code="ENG-Premier League",
            home_team="Arsenal", away_team="Chelsea", market_type="1x2", selection="home",
            odds=1.45, probability=0.75, expected_value=0.08,
        ),
        CandidateLeg(
            prediction_id=2, match_id=999, league_code="ENG-Premier League",
            home_team="Arsenal", away_team="Chelsea", market_type="over_under_2.5", selection="over",
            odds=1.50, probability=0.72, expected_value=0.08,
        ),
    ]

    slips = SlipCombinator.generate_slips(candidates, category="banker_rollover", max_results=3)
    # Should be empty because at most 1 leg per match is permitted
    assert len(slips) == 0
