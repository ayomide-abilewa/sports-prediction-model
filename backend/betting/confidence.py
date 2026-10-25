from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import structlog
from backend.config import settings

logger = structlog.get_logger()


@dataclass
class ConfidenceEvaluation:
    tier: str | None  # "Tier 1: Bankers", "Tier 2: Solid Core", etc.
    is_value: bool
    expected_value: float
    probability: float
    odds: float
    quality_score: float
    reasons: list[str]


class ConfidenceClassifier:
    """Configurable 4-Tier confidence classification engine per Master Directive Section 10."""

    TIERS = {
        "tier_1_bankers": {
            "name": "Tier 1 – Bankers",
            "min_prob": 0.75,
            "max_prob": 0.92,
            "min_odds": 1.15,
            "max_odds": 1.40,
            "min_quality": 0.60,
        },
        "tier_2_solid_core": {
            "name": "Tier 2 – Solid Core",
            "min_prob": 0.60,
            "max_prob": 0.749,
            "min_odds": 1.38,
            "max_odds": 1.75,
            "min_quality": 0.50,
        },
        "tier_3_sharp_value": {
            "name": "Tier 3 – Sharp Value",
            "min_prob": 0.45,
            "max_prob": 0.599,
            "min_odds": 1.70,
            "max_odds": 2.40,
            "min_quality": 0.50,
        },
        "tier_4_high_yield": {
            "name": "Tier 4 – High Yield",
            "min_prob": 0.28,
            "max_prob": 0.449,
            "min_odds": 2.35,
            "max_odds": 4.50,
            "min_quality": 0.50,
        },
    }

    def __init__(self, min_ev_threshold: float = settings.min_ev_threshold):
        self.min_ev_threshold = min_ev_threshold

    def evaluate(
        self,
        model_prob: float,
        available_odds: float,
        quality_score: float = 1.0,
    ) -> ConfidenceEvaluation:
        """Evaluates a betting selection against statistical and market criteria."""
        ev = round((model_prob * available_odds) - 1.0, 4)
        is_value = ev >= self.min_ev_threshold
        reasons: list[str] = []

        if not is_value:
            reasons.append(f"EV ({ev:.1%}) below required threshold ({self.min_ev_threshold:.1%})")

        assigned_tier: str | None = None

        if is_value:
            for _, t_conf in self.TIERS.items():
                if (
                    t_conf["min_prob"] <= model_prob <= t_conf["max_prob"]
                    and t_conf["min_odds"] <= available_odds <= t_conf["max_odds"]
                    and quality_score >= t_conf["min_quality"]
                ):
                    assigned_tier = t_conf["name"]
                    break

            if not assigned_tier:
                reasons.append("Selection does not meet standard probability/odds bounding box")

        return ConfidenceEvaluation(
            tier=assigned_tier,
            is_value=is_value,
            expected_value=ev,
            probability=model_prob,
            odds=available_odds,
            quality_score=quality_score,
            reasons=reasons,
        )
