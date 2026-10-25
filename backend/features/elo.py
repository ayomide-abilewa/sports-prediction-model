from __future__ import annotations

import math
from typing import Any
import structlog
from backend.config import settings

logger = structlog.get_logger()


class EloRatingSystem:
    """Dynamic Elo rating system tailored for football.
    
    Features:
    - Configurable home advantage adjustment (default +100 elo)
    - Margin of victory / goal difference multiplier
    - Dynamic K-factor
    """

    def __init__(
        self,
        default_rating: float = settings.default_elo,
        k_factor: float = settings.elo_k_factor,
        home_advantage: float = settings.elo_home_advantage,
    ):
        self.default_rating = default_rating
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.ratings: dict[int, float] = {}  # team_id -> current_elo

    def get_rating(self, team_id: int) -> float:
        """Retrieves current rating for a team, or defaults."""
        return self.ratings.get(team_id, self.default_rating)

    def set_rating(self, team_id: int, rating: float) -> None:
        self.ratings[team_id] = float(rating)

    def expected_outcome(self, rating_a: float, rating_b: float) -> float:
        """Calculates win probability for team A against team B."""
        return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))

    def update(
        self,
        home_team_id: int,
        away_team_id: int,
        home_goals: int,
        away_goals: int,
    ) -> tuple[float, float]:
        """Calculates updated ratings after a match result.
        
        Returns:
            (new_home_rating, new_away_rating)
        """
        r_home = self.get_rating(home_team_id)
        r_away = self.get_rating(away_team_id)

        # Apply home advantage to expected calculation
        adj_home_rating = r_home + self.home_advantage
        exp_home = self.expected_outcome(adj_home_rating, r_away)
        exp_away = 1.0 - exp_home

        # Determine actual match result (1 = win, 0.5 = draw, 0 = loss)
        if home_goals > away_goals:
            act_home, act_away = 1.0, 0.0
        elif home_goals == away_goals:
            act_home, act_away = 0.5, 0.5
        else:
            act_home, act_away = 0.0, 1.0

        # Goal difference scaling multiplier: ln(abs(GD) + 1)
        gd = abs(home_goals - away_goals)
        gd_mult = math.log(max(gd, 1) + 1.0)

        # Rating delta
        delta_home = self.k_factor * gd_mult * (act_home - exp_home)
        delta_away = self.k_factor * gd_mult * (act_away - exp_away)

        new_home = round(r_home + delta_home, 2)
        new_away = round(r_away + delta_away, 2)

        self.ratings[home_team_id] = new_home
        self.ratings[away_team_id] = new_away

        return new_home, new_away
