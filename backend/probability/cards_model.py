from __future__ import annotations

import math
from typing import Any
import numpy as np
import pandas as pd
from scipy.stats import nbinom
import structlog

logger = structlog.get_logger()


class CardsModel:
    """Negative Binomial regression model for match bookings/cards predictions per Master Directive Section 6.6."""

    def __init__(self, dispersion: float = 0.20):
        self.dispersion = dispersion  # alpha
        self.base_total_cards = 4.10
        self.referee_multipliers: dict[str, float] = {}
        self.team_card_rates: dict[str, float] = {}

    def fit(self, matches_df: pd.DataFrame) -> CardsModel:
        """Estimates baseline card tendencies from historical match records."""
        if matches_df.empty or "home_yellows" not in matches_df.columns:
            return self

        df = matches_df.dropna(subset=["home_yellows", "away_yellows"])
        if len(df) < 20:
            return self

        total_cards = df["home_yellows"] + df["away_yellows"]
        self.base_total_cards = float(total_cards.mean())
        return self

    def predict_cards(
        self,
        home_team: str,
        away_team: str,
        referee_name: str | None = None,
        is_derby: bool = False,
    ) -> dict[str, Any]:
        """Calculates expected card rates and Over/Under market probabilities."""
        base = self.base_total_cards

        # Referee adjustment factor
        ref_mult = self.referee_multipliers.get(referee_name or "", 1.0)
        # Derby / Rivalry emotional friction factor
        derby_mult = 1.25 if is_derby else 1.0

        exp_total = round(base * ref_mult * derby_mult, 2)
        exp_home = round(exp_total * 0.48, 2)
        exp_away = round(exp_total * 0.52, 2)

        alpha = max(self.dispersion, 1e-4)
        p = 1.0 / (1.0 + alpha * exp_total)
        n = 1.0 / alpha

        lines = [2.5, 3.5, 4.5, 5.5, 6.5]
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
            "expected_cards": {
                "home": exp_home,
                "away": exp_away,
                "total": exp_total,
            },
            "derby_factor_applied": is_derby,
            "referee": referee_name or "Standard",
            "totals": ou_probs,
        }
