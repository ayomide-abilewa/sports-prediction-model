from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import structlog

logger = structlog.get_logger()


@dataclass
class StakeRecommendation:
    method: str
    stake_amount: float
    stake_percentage: float
    bankroll_remaining: float
    warning: str | None = None


class BankrollEngine:
    """Quantitative bankroll management and staking simulator."""

    def __init__(
        self,
        bankroll: float = 1000.0,
        max_single_exposure_pct: float = 0.05,  # Max 5% on any single selection
        kelly_fraction: float = 0.25,          # Quarter-Kelly default (conservative)
    ):
        self.bankroll = bankroll
        self.max_single_exposure_pct = max_single_exposure_pct
        self.kelly_fraction = kelly_fraction

    def calculate_kelly_stake(
        self,
        model_prob: float,
        decimal_odds: float,
        custom_bankroll: float | None = None,
    ) -> StakeRecommendation:
        """Calculates fractional Kelly stake amount:
        
        f* = [p * (b - 1) - (1 - p)] / (b - 1)
        stake = bankroll * f* * fraction
        """
        b = decimal_odds
        p = model_prob
        br = custom_bankroll or self.bankroll

        if b <= 1.0 or p <= 0.0 or p >= 1.0:
            return StakeRecommendation(
                method="fractional_kelly",
                stake_amount=0.0,
                stake_percentage=0.0,
                bankroll_remaining=br,
                warning="Invalid probability or odds",
            )

        # Full Kelly fraction
        b_net = b - 1.0
        q = 1.0 - p
        full_kelly = (p * b_net - q) / b_net

        if full_kelly <= 0.0:
            # Negative expected value -> zero stake
            return StakeRecommendation(
                method="fractional_kelly",
                stake_amount=0.0,
                stake_percentage=0.0,
                bankroll_remaining=br,
                warning="Negative expected value (Kelly <= 0)",
            )

        # Apply conservative fraction (e.g. Quarter Kelly)
        target_pct = full_kelly * self.kelly_fraction
        capped_pct = min(target_pct, self.max_single_exposure_pct)

        stake = round(br * capped_pct, 2)
        warning = None
        if target_pct > self.max_single_exposure_pct:
            warning = f"Kelly recommendation ({target_pct:.1%}) capped at max exposure ({self.max_single_exposure_pct:.1%})"

        return StakeRecommendation(
            method=f"{self.kelly_fraction:.2f}_kelly",
            stake_amount=stake,
            stake_percentage=round(capped_pct, 4),
            bankroll_remaining=round(br - stake, 2),
            warning=warning,
        )

    def calculate_flat_stake(
        self,
        stake_pct: float = 0.02,
        custom_bankroll: float | None = None,
    ) -> StakeRecommendation:
        """Calculates fixed-percentage unit stake (e.g. 2% per bet)."""
        br = custom_bankroll or self.bankroll
        pct = min(stake_pct, self.max_single_exposure_pct)
        stake = round(br * pct, 2)
        return StakeRecommendation(
            method="flat_stake",
            stake_amount=stake,
            stake_percentage=round(pct, 4),
            bankroll_remaining=round(br - stake, 2),
        )
