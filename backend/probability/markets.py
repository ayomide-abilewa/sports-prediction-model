from __future__ import annotations

from typing import Any
import numpy as np


class MarketEngine:
    """Standardizes probability outputs and calculates fair odds and implied margins."""

    @staticmethod
    def calculate_fair_odds(probability: float, min_prob: float = 0.001) -> float:
        """Calculates fair decimal odds (1 / P)."""
        clamped = max(probability, min_prob)
        return round(1.0 / clamped, 2)

    @staticmethod
    def remove_bookmaker_margin(odds_dict: dict[str, float]) -> dict[str, float]:
        """Removes the bookmaker overround from a set of mutually exclusive outcomes.
        
        Args:
            odds_dict: e.g. {"home": 2.10, "draw": 3.40, "away": 3.60}
            
        Returns:
            Dictionary of true margin-adjusted implied probabilities summing to 1.0.
        """
        raw_implied = {k: (1.0 / v) for k, v in odds_dict.items() if v > 1.0}
        total_margin = sum(raw_implied.values())
        if total_margin <= 0:
            return {k: 1.0 / len(odds_dict) for k in odds_dict}

        # Normalize by total margin (basic proportional normalization)
        return {k: round(v / total_margin, 4) for k, v in raw_implied.items()}

    @staticmethod
    def calculate_expected_value(model_probability: float, available_odds: float) -> float:
        """Calculates Expected Value (EV):
            EV = (Model Probability × Decimal Odds) - 1.0
            
        Returns:
            Float representing EV (e.g. +0.075 for +7.5% EV)
        """
        if available_odds <= 1.0:
            return -1.0
        return round((model_probability * available_odds) - 1.0, 4)
