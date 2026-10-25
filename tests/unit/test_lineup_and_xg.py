from __future__ import annotations

import pandas as pd
from backend.probability.lineup_intelligence import LineupIntelligenceEngine
from backend.probability.xg_model import ExpectedGoalsTeamStrengthModel


def test_lineup_pre_lineup_mode():
    res = LineupIntelligenceEngine.evaluate_lineup_impact(
        home_team="Arsenal",
        away_team="Chelsea",
        expected_lineup=["Saka", "Saliba", "Rice", "Havertz"],
        confirmed_lineup=None,
    )
    assert res.status == "predicted"
    assert res.recalculation_recommended is False
    assert res.home_squad_strength_delta == 0.0


def test_lineup_confirmed_omission():
    expected = ["Saka", "Saliba", "Rice", "Havertz"]
    confirmed = ["Saliba", "Rice", "Havertz", "Trossard"]  # Saka omitted

    res = LineupIntelligenceEngine.evaluate_lineup_impact(
        home_team="Arsenal",
        away_team="Chelsea",
        expected_lineup=expected,
        confirmed_lineup=confirmed,
    )
    assert res.status == "confirmed"
    assert res.recalculation_recommended is True
    assert "Saka" in res.key_omissions
    assert res.home_squad_strength_delta < 0.0


def test_xg_team_strength_model():
    df = pd.DataFrame([
        {"home_team": "Arsenal", "away_team": "Chelsea", "ft_home_goals": 3, "ft_away_goals": 1},
        {"home_team": "Chelsea", "away_team": "Arsenal", "ft_home_goals": 0, "ft_away_goals": 2},
    ])
    model = ExpectedGoalsTeamStrengthModel()
    model.fit(df)
    pred = model.predict_match_xg("Arsenal", "Chelsea")

    assert "projected_xg" in pred
    assert pred["projected_xg"]["home"] > 0
    assert pred["projected_xg"]["away"] > 0
    assert pred["projected_xg"]["total"] > 0
