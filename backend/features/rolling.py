from __future__ import annotations

from datetime import datetime
from typing import Any
import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger()


class RollingFeatureEngine:
    """Computes rolling window team metrics with strict anti-data-leakage guarantees.
    
    CRITICAL: Only matches completed strictly BEFORE target match kickoff are included.
    """

    WINDOWS: list[int] = [5, 10]

    @classmethod
    def compute_team_rolling_stats(
        cls,
        team_id: int,
        match_history: pd.DataFrame,
        before_kickoff: datetime,
    ) -> dict[str, float]:
        """Calculates rolling statistics for a team.
        
        Args:
            team_id: Target team ID
            match_history: DataFrame containing completed matches
            before_kickoff: Kickoff threshold (exclusive)
        """
        features: dict[str, float] = {}

        if match_history.empty:
            return cls._default_features()

        # Strict temporal filter
        df = match_history[
            (match_history["kickoff"] < before_kickoff)
            & (
                (match_history["home_team_id"] == team_id)
                | (match_history["away_team_id"] == team_id)
            )
        ].sort_values("kickoff", ascending=False)

        if df.empty:
            return cls._default_features()

        # Build team perspective rows
        team_rows: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            is_home = (row["home_team_id"] == team_id)
            gf = row["ft_home_goals"] if is_home else row["ft_away_goals"]
            ga = row["ft_away_goals"] if is_home else row["ft_home_goals"]
            sf = row.get("home_shots" if is_home else "away_shots", np.nan)
            sa = row.get("away_shots" if is_home else "home_shots", np.nan)
            cf = row.get("home_corners" if is_home else "away_corners", np.nan)
            ca = row.get("away_corners" if is_home else "home_corners", np.nan)
            yf = row.get("home_yellows" if is_home else "away_yellows", np.nan)

            team_rows.append({
                "goals_for": gf,
                "goals_against": ga,
                "shots_for": sf,
                "shots_against": sa,
                "corners_for": cf,
                "corners_against": ca,
                "yellows": yf,
                "points": 3 if gf > ga else (1 if gf == ga else 0),
            })

        t_df = pd.DataFrame(team_rows)

        for w in cls.WINDOWS:
            sample = t_df.head(w)
            n_matches = len(sample)
            if n_matches == 0:
                continue

            features[f"gf_avg_{w}"] = round(float(sample["goals_for"].mean()), 2)
            features[f"ga_avg_{w}"] = round(float(sample["goals_against"].mean()), 2)
            features[f"points_avg_{w}"] = round(float(sample["points"].mean()), 2)

            if "shots_for" in sample.columns and not sample["shots_for"].isna().all():
                features[f"shots_avg_{w}"] = round(float(sample["shots_for"].dropna().mean()), 2)
            if "corners_for" in sample.columns and not sample["corners_for"].isna().all():
                features[f"corners_avg_{w}"] = round(float(sample["corners_for"].dropna().mean()), 2)
            if "yellows" in sample.columns and not sample["yellows"].isna().all():
                features[f"cards_avg_{w}"] = round(float(sample["yellows"].dropna().mean()), 2)

        return features

    @classmethod
    def _default_features(cls) -> dict[str, float]:
        """Provides neutral shrinkage default features when no history exists."""
        defaults = {}
        for w in cls.WINDOWS:
            defaults[f"gf_avg_{w}"] = 1.30
            defaults[f"ga_avg_{w}"] = 1.30
            defaults[f"points_avg_{w}"] = 1.20
            defaults[f"shots_avg_{w}"] = 11.0
            defaults[f"corners_avg_{w}"] = 5.0
            defaults[f"cards_avg_{w}"] = 1.8
        return defaults
