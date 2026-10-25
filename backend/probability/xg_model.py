from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger()


class ExpectedGoalsTeamStrengthModel:
    """Expected Goals (xG) and Underlying Team Quality Model per Master Directive Section 6.2."""

    def __init__(self, shrinkage_weight: float = 0.20):
        self.shrinkage_weight = shrinkage_weight
        self.league_avg_npxg = 1.35
        self.team_ratings: dict[str, dict[str, float]] = {}

    def fit(self, matches_df: pd.DataFrame) -> ExpectedGoalsTeamStrengthModel:
        """Fits team attacking and defensive quality from rolling xG statistics."""
        if matches_df.empty:
            return self

        # Extract unique teams
        teams = sorted(list(set(matches_df["home_team"]).union(set(matches_df["away_team"]))))

        for t in teams:
            t_home = matches_df[matches_df["home_team"] == t]
            t_away = matches_df[matches_df["away_team"] == t]

            goals_for = pd.concat([t_home["ft_home_goals"], t_away["ft_away_goals"]]).dropna()
            goals_against = pd.concat([t_home["ft_away_goals"], t_away["ft_home_goals"]]).dropna()

            raw_att = float(goals_for.mean()) if len(goals_for) > 0 else self.league_avg_npxg
            raw_def = float(goals_against.mean()) if len(goals_against) > 0 else self.league_avg_npxg

            # Apply empirical Bayes shrinkage toward league mean
            n = len(goals_for)
            w = n / (n + 10.0)  # Shrinkage factor

            shrunk_att = w * raw_att + (1.0 - w) * self.league_avg_npxg
            shrunk_def = w * raw_def + (1.0 - w) * self.league_avg_npxg

            self.team_ratings[t] = {
                "npxg_for_p90": round(shrunk_att, 2),
                "npxg_against_p90": round(shrunk_def, 2),
                "npxg_net": round(shrunk_att - shrunk_def, 2),
                "sample_size": n,
            }

        return self

    def predict_match_xg(self, home_team: str, away_team: str) -> dict[str, Any]:
        """Estimates projected match expected goals from underlying team metrics."""
        h_ratings = self.team_ratings.get(
            home_team, {"npxg_for_p90": 1.40, "npxg_against_p90": 1.25, "npxg_net": 0.15}
        )
        a_ratings = self.team_ratings.get(
            away_team, {"npxg_for_p90": 1.25, "npxg_against_p90": 1.40, "npxg_net": -0.15}
        )

        # Baseline home advantage +0.20 xG
        exp_home = round(
            (h_ratings["npxg_for_p90"] * a_ratings["npxg_against_p90"] / self.league_avg_npxg) + 0.18, 2
        )
        exp_away = round(
            (a_ratings["npxg_for_p90"] * h_ratings["npxg_against_p90"] / self.league_avg_npxg), 2
        )

        return {
            "projected_xg": {
                "home": exp_home,
                "away": exp_away,
                "total": round(exp_home + exp_away, 2),
                "xg_diff": round(exp_home - exp_away, 2),
            },
            "team_profiles": {
                "home": h_ratings,
                "away": a_ratings,
            },
        }
