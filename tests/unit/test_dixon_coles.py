from __future__ import annotations

from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import pytest
from backend.probability.dixon_coles import DixonColesModel


@pytest.fixture
def sample_match_data():
    """Generates synthetic historical matches between 4 teams."""
    teams = ["Arsenal", "Chelsea", "Liverpool", "Manchester City"]
    data = []
    base_date = datetime(2024, 1, 1)

    for i in range(40):
        h = teams[i % 4]
        a = teams[(i + 1) % 4]
        # Realistic scores
        hg = (i + 1) % 3
        ag = i % 2
        data.append({
            "home_team": h,
            "away_team": a,
            "ft_home_goals": hg,
            "ft_away_goals": ag,
            "kickoff": base_date + timedelta(days=i * 3),
        })

    return pd.DataFrame(data)


def test_dixon_coles_fit_and_predict(sample_match_data):
    model = DixonColesModel(xi=0.005)
    model.fit(sample_match_data)

    assert model.is_fitted
    assert len(model.attack_strengths) == 4
    assert len(model.defense_strengths) == 4
    assert 0.0 <= model.home_advantage <= 1.0

    # Probability Matrix checks
    matrix = model.predict_scoreline_matrix("Arsenal", "Chelsea")
    assert matrix.shape == (11, 11)
    assert np.isclose(np.sum(matrix), 1.0, atol=1e-3)

    # Full Match Prediction
    pred = model.predict_match("Arsenal", "Chelsea")
    p1x2 = pred["1x2"]
    total_1x2 = p1x2["home"] + p1x2["draw"] + p1x2["away"]
    assert np.isclose(total_1x2, 1.0, atol=1e-2)

    # Over/Under checks
    totals = pred["totals"]
    assert "over_under_2.5" in totals
    ou25 = totals["over_under_2.5"]
    assert np.isclose(ou25["over"] + ou25["under"], 1.0, atol=1e-3)

    # Both teams to score checks
    btts = pred["btts"]
    assert np.isclose(btts["yes"] + btts["no"], 1.0, atol=1e-3)


def test_dixon_coles_unfitted_raises():
    model = DixonColesModel()
    with pytest.raises(ValueError):
        model.predict_scoreline_matrix("Arsenal", "Chelsea")
