from __future__ import annotations

from datetime import datetime
from backend.ingestion.validation import DataValidator


def test_validate_match_valid():
    validator = DataValidator()
    match = {
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "kickoff": datetime.utcnow(),
        "ft_home_goals": 2,
        "ft_away_goals": 1,
        "ht_home_goals": 1,
        "ht_away_goals": 0,
    }
    errors = validator.validate_match(match)
    assert len(errors) == 0


def test_validate_match_invalid_scores():
    validator = DataValidator()

    # Negative goals
    errors = validator.validate_match({
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "kickoff": datetime.utcnow(),
        "ft_home_goals": -1,
        "ft_away_goals": 1,
    })
    assert any("Negative" in e for e in errors)

    # Half time > Full time
    errors = validator.validate_match({
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "kickoff": datetime.utcnow(),
        "ft_home_goals": 1,
        "ft_away_goals": 0,
        "ht_home_goals": 2,
        "ht_away_goals": 0,
    })
    assert any("exceed" in e for e in errors)

    # Same team playing itself
    errors = validator.validate_match({
        "home_team": "Arsenal",
        "away_team": "Arsenal",
        "kickoff": datetime.utcnow(),
    })
    assert any("same team" in e for e in errors)


def test_validate_match_statistics():
    validator = DataValidator()

    # Invalid: shots on target > shots
    errors = validator.validate_match_statistics({
        "shots": 5,
        "shots_on_target": 8,
    })
    assert any("cannot exceed" in e for e in errors)

    # Abnormal corners
    errors = validator.validate_match_statistics({
        "corners": 45,
    })
    assert any("Abnormal corner" in e for e in errors)


def test_validate_odds():
    validator = DataValidator()

    # Valid odds
    assert len(validator.validate_odds({"odds": 1.85})) == 0

    # Invalid: odds <= 1.00
    errors = validator.validate_odds({"odds": 0.95})
    assert any("strictly > 1.00" in e for e in errors)

    # Missing odds
    errors = validator.validate_odds({})
    assert any("cannot be None" in e for e in errors)


def test_calculate_quality_score():
    validator = DataValidator()

    # Complete match record
    match = {
        "home_team": "Liverpool",
        "away_team": "Everton",
        "kickoff": datetime.utcnow(),
        "ft_home_goals": 2,
        "ft_away_goals": 0,
        "ht_home_goals": 1,
        "ht_away_goals": 0,
        "odds": [{"odds": 1.45}],
    }
    stats = [
        {"shots": 15, "corners": 7, "yellow_cards": 2},
        {"shots": 4, "corners": 1, "yellow_cards": 4},
    ]

    score = validator.calculate_quality_score(match, stats)
    assert score == 1.0

    # Incomplete match record
    minimal_match = {
        "home_team": "Liverpool",
        "away_team": "Everton",
        "kickoff": datetime.utcnow(),
    }
    score_min = validator.calculate_quality_score(minimal_match, [])
    assert 0.0 < score_min < 0.5
