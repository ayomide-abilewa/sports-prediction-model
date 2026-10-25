from __future__ import annotations

from datetime import datetime
from typing import Any
import structlog

logger = structlog.get_logger()


class DataValidator:
    """Automated data quality engine.
    
    Verifies match integrity, detects anomalies, and computes completeness scores.
    """

    @staticmethod
    def validate_match(match: dict[str, Any]) -> list[str]:
        """Validates match record dictionary before ingestion."""
        errors: list[str] = []

        home = match.get("home_team")
        away = match.get("away_team")
        if not home or not away:
            errors.append("Missing home or away team name")
        elif home.strip().lower() == away.strip().lower():
            errors.append(f"Invalid match: same team ({home}) playing itself")

        kickoff = match.get("kickoff")
        if not kickoff:
            errors.append("Missing kickoff timestamp")

        # Score checks
        fthg = match.get("ft_home_goals")
        ftag = match.get("ft_away_goals")
        if fthg is not None and fthg < 0:
            errors.append(f"Negative home goals: {fthg}")
        if ftag is not None and ftag < 0:
            errors.append(f"Negative away goals: {ftag}")
        if fthg is not None and fthg > 20:
            errors.append(f"Abnormally high home goals: {fthg}")
        if ftag is not None and ftag > 20:
            errors.append(f"Abnormally high away goals: {ftag}")

        hthg = match.get("ht_home_goals")
        htag = match.get("ht_away_goals")
        if hthg is not None and fthg is not None and hthg > fthg:
            errors.append(f"Half-time home goals ({hthg}) exceed full-time ({fthg})")
        if htag is not None and ftag is not None and htag > ftag:
            errors.append(f"Half-time away goals ({htag}) exceed full-time ({ftag})")

        return errors

    @staticmethod
    def validate_match_statistics(stats: dict[str, Any]) -> list[str]:
        """Validates team match statistics."""
        errors: list[str] = []

        shots = stats.get("shots")
        sot = stats.get("shots_on_target")
        if shots is not None and shots < 0:
            errors.append(f"Negative shots: {shots}")
        if sot is not None and sot < 0:
            errors.append(f"Negative shots on target: {sot}")
        if shots is not None and sot is not None and sot > shots:
            errors.append(f"Shots on target ({sot}) cannot exceed total shots ({shots})")

        corners = stats.get("corners")
        if corners is not None and (corners < 0 or corners > 30):
            errors.append(f"Abnormal corner count: {corners}")

        fouls = stats.get("fouls")
        if fouls is not None and (fouls < 0 or fouls > 50):
            errors.append(f"Abnormal foul count: {fouls}")

        yellows = stats.get("yellow_cards")
        if yellows is not None and (yellows < 0 or yellows > 15):
            errors.append(f"Abnormal yellow card count: {yellows}")

        reds = stats.get("red_cards")
        if reds is not None and (reds < 0 or reds > 5):
            errors.append(f"Abnormal red card count: {reds}")

        return errors

    @staticmethod
    def validate_odds(odds_dict: dict[str, Any]) -> list[str]:
        """Validates market odds values."""
        errors: list[str] = []
        odds_val = odds_dict.get("odds")

        if odds_val is None:
            errors.append("Odds value cannot be None")
        elif odds_val <= 1.00:
            errors.append(f"Decimal odds must be strictly > 1.00, got {odds_val}")
        elif odds_val > 1000.0:
            errors.append(f"Abnormally high odds value: {odds_val}")

        return errors

    @staticmethod
    def calculate_quality_score(match: dict[str, Any], stats: list[dict[str, Any]] | None = None) -> float:
        """Calculates a normalized data quality score [0.0 - 1.0]."""
        score = 0.0
        total_weight = 100.0

        # Core match info (30 points)
        if match.get("home_team") and match.get("away_team"):
            score += 10.0
        if match.get("kickoff"):
            score += 10.0
        if match.get("ft_home_goals") is not None and match.get("ft_away_goals") is not None:
            score += 10.0

        # Half time score (10 points)
        if match.get("ht_home_goals") is not None and match.get("ht_away_goals") is not None:
            score += 10.0

        # Detailed match statistics (30 points)
        if stats:
            has_shots = any(s.get("shots") is not None for s in stats)
            has_corners = any(s.get("corners") is not None for s in stats)
            has_cards = any(s.get("yellow_cards") is not None for s in stats)
            if has_shots:
                score += 10.0
            if has_corners:
                score += 10.0
            if has_cards:
                score += 10.0

        # Odds availability (30 points)
        odds = match.get("odds") or []
        if odds:
            score += 30.0

        return round(score / total_weight, 2)


data_validator = DataValidator()
