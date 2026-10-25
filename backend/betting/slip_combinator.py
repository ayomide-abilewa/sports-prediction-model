from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any
import structlog
from backend.betting.correlation import CorrelationEngine

logger = structlog.get_logger()


@dataclass
class CandidateLeg:
    prediction_id: int
    match_id: int
    league_code: str
    home_team: str
    away_team: str
    market_type: str
    selection: str
    odds: float
    probability: float
    expected_value: float
    kickoff: str | None = None


@dataclass
class GeneratedSlipResult:
    category: str
    slip_name: str
    legs: list[CandidateLeg]
    combined_odds: float
    joint_probability: float
    expected_return: float
    risk_class: str
    warnings: list[str] = field(default_factory=list)


class SlipCombinator:
    """Intelligent Accumulator and Combinator Engine supporting the 5 Blueprint Products."""

    RECIPES: dict[str, dict[str, Any]] = {
        "banker_rollover": {
            "name": "Product 1: Banker Rollover",
            "target_odds": (1.80, 2.60),
            "legs_range": (2, 3),
            "min_leg_prob": 0.70,
            "min_leagues": 1,
            "risk_class": "Low Risk",
        },
        "solid_core": {
            "name": "Product 2: Solid Core Multiplier",
            "target_odds": (4.50, 7.50),
            "legs_range": (3, 5),
            "min_leg_prob": 0.55,
            "min_leagues": 1,
            "risk_class": "Moderate Risk",
        },
        "sharp_multi": {
            "name": "Product 3: Sharp Multi-League Builder",
            "target_odds": (11.0, 22.0),
            "legs_range": (5, 7),
            "min_leg_prob": 0.45,
            "min_leagues": 3,
            "risk_class": "Elevated Risk",
        },
        "high_yield": {
            "name": "Product 4: Weekend High-Yield Builder",
            "target_odds": (35.0, 150.0),
            "legs_range": (6, 10),
            "min_leg_prob": 0.25,
            "min_leagues": 2,
            "risk_class": "Very High Risk",
        },
        "corners_cards": {
            "name": "Product 5: Corners and Cards Specialist",
            "target_odds": (3.20, 6.50),
            "legs_range": (3, 4),
            "min_leg_prob": 0.50,
            "min_leagues": 1,
            "risk_class": "Moderate Risk",
        },
    }

    @classmethod
    def generate_slips(
        cls,
        candidate_pool: list[CandidateLeg],
        category: str,
        max_results: int = 5,
    ) -> list[GeneratedSlipResult]:
        """Generates ranked accumulator combinations for a selected recipe."""
        recipe = cls.RECIPES.get(category)
        if not recipe:
            raise ValueError(f"Unknown slip category: {category}")

        min_odds, max_odds = recipe["target_odds"]
        min_legs, max_legs = recipe["legs_range"]
        min_prob = recipe["min_leg_prob"]
        min_leagues = recipe.get("min_leagues", 1)

        # Filter candidates meeting minimum probability and sort by Expected Value
        eligible_legs = [c for c in candidate_pool if c.probability >= min_prob and c.odds > 1.05]
        # Sort by expected value descending and prune to top 16 candidates to prevent combinatorial explosion
        eligible_legs.sort(key=lambda x: x.expected_value, reverse=True)
        eligible_legs = eligible_legs[:16]

        if len(eligible_legs) < min_legs:
            logger.info("insufficient_legs_for_recipe", category=category, eligible=len(eligible_legs))
            return []

        valid_slips: list[GeneratedSlipResult] = []

        # Search across allowed leg counts
        for leg_count in range(min_legs, max_legs + 1):
            if leg_count > len(eligible_legs):
                break

            for combo in itertools.combinations(eligible_legs, leg_count):
                # 1. Verification: At most 1 leg per match (unless allowed by correlation engine)
                match_ids = [leg.match_id for leg in combo]
                if len(set(match_ids)) != len(match_ids):
                    continue

                # 2. League diversification constraint
                distinct_leagues = len(set(leg.league_code for leg in combo))
                if distinct_leagues < min_leagues:
                    continue

                # 3. Combined decimal odds
                combined_odds = 1.0
                for leg in combo:
                    combined_odds *= leg.odds
                combined_odds = round(combined_odds, 2)

                if not (min_odds <= combined_odds <= max_odds):
                    continue

                # 4. Joint probability and correlation adjustments
                joint_prob = 1.0
                warnings: list[str] = []
                for leg in combo:
                    joint_prob *= leg.probability

                # 5. Compound Expected Return
                exp_return = round((combined_odds * joint_prob) - 1.0, 4)

                valid_slips.append(
                    GeneratedSlipResult(
                        category=category,
                        slip_name=recipe["name"],
                        legs=list(combo),
                        combined_odds=combined_odds,
                        joint_probability=round(joint_prob, 4),
                        expected_return=exp_return,
                        risk_class=recipe["risk_class"],
                        warnings=warnings,
                    )
                )

                if len(valid_slips) >= max_results * 5:
                    break

        # Sort by expected return descending
        valid_slips.sort(key=lambda s: s.expected_return, reverse=True)
        return valid_slips[:max_results]
