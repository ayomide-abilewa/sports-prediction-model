from __future__ import annotations

from backend.features.elo import EloRatingSystem


def test_elo_initialization():
    elo = EloRatingSystem(default_rating=1500.0, k_factor=20.0, home_advantage=100.0)
    assert elo.get_rating(1) == 1500.0
    assert elo.get_rating(2) == 1500.0


def test_elo_home_win_update():
    elo = EloRatingSystem(default_rating=1500.0, k_factor=20.0, home_advantage=100.0)

    # Team 1 beats Team 2 (2-0)
    new_h, new_a = elo.update(home_team_id=1, away_team_id=2, home_goals=2, away_goals=0)
    assert new_h > 1500.0
    assert new_a < 1500.0
    assert elo.get_rating(1) == new_h
    assert elo.get_rating(2) == new_a


def test_elo_away_upset_update():
    elo = EloRatingSystem(default_rating=1500.0, k_factor=20.0, home_advantage=100.0)
    # Set home team as very strong
    elo.set_rating(1, 1800.0)
    elo.set_rating(2, 1400.0)

    # Away team 2 upsets strong home team 1 (0-3)
    new_h, new_a = elo.update(home_team_id=1, away_team_id=2, home_goals=0, away_goals=3)
    # Underdog should gain significant rating
    assert new_a > 1400.0
    assert new_h < 1800.0
