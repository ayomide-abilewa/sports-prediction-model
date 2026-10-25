from __future__ import annotations

import math
from typing import Any
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import nbinom
import structlog

logger = structlog.get_logger()


class CornersModel:
    """Negative Binomial regression model for match corner count predictions.
    
    Models overdispersion in corner events (variance > mean) per Master Directive Section 6.5.
    """

    def __init__(self, dispersion: float = 0.15):
        self.dispersion = dispersion  # alpha in Var = mu + alpha * mu^2
        self.base_home_corners = 5.4
        self.base_away_corners = 4.2
        self.team_corner_attack: dict[str, float] = {}
        self.team_corner_defense: dict[str, float] = {}
        self.is_fitted = False

    def fit(self, matches_df: pd.DataFrame) -> CornersModel:
        """Estimates team-specific corner tendencies from historical match stats."""
        if matches_df.empty or "home_corners" not in matches_df.columns:
            self.is_fitted = True
            return self

        df = matches_df.dropna(subset=["home_corners", "away_corners"])
        if len(df) < 20:
            self.is_fitted = True
            return self

        self.base_home_corners = float(df["home_corners"].mean())
        self.base_away_corners = float(df["away_corners"].mean())

        teams = sorted(list(set(df["home_team"]).union(set(df["away_team"]))))
        for t in teams:
            t_home = df[df["home_team"] == t]["home_corners"]
            t_away = df[df["away_team"] == t]["away_corners"]
            t_for = pd.concat([t_home, t_away]) if not t_home.empty or not t_away.empty else pd.Series([5.0])

            # Attack ratio relative to league mean
            self.team_corner_attack[t] = float(t_for.mean() / ((self.base_home_corners + self.base_away_corners) / 2.0))

        self.is_fitted = True
        return self

    def predict_corners(self, home_team: str, away_team: str) -> dict[str, Any]:
        """Calculates expected corner rates and Over/Under market probabilities."""
        att_h = self.team_corner_attack.get(home_team, 1.0)
        att_a = self.team_corner_attack.get(away_team, 1.0)

        exp_home = round(self.base_home_corners * att_h, 2)
        exp_away = round(self.base_away_corners * att_a, 2)
        exp_total = round(exp_home + exp_away, 2)

        # Convert mean (mu) and dispersion (alpha) to SciPy nbinom parameters (n, p)
        # Var = mu + alpha * mu^2
        # p = mu / Var = 1 / (1 + alpha * mu)
        # n = mu^2 / (Var - mu) = 1 / alpha
        alpha = max(self.dispersion, 1e-4)
        p = 1.0 / (1.0 + alpha * exp_total)
        n = 1.0 / alpha

        lines = [6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5]
        ou_probs: dict[str, dict[str, float]] = {}

        for line in lines:
            k = int(math.floor(line))
            under_prob = float(nbinom.cdf(k, n, p))
            over_prob = float(1.0 - under_prob)
            ou_probs[f"over_under_{line}"] = {
                "over": round(over_prob, 4),
                "under": round(under_prob, 4),
            }

        return {
            "expected_corners": {
                "home": exp_home,
                "away": exp_away,
                "total": exp_total,
            },
            "dispersion_alpha": self.dispersion,
            "totals": ou_probs,
        }
