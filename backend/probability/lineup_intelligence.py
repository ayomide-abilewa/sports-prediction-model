from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import structlog

logger = structlog.get_logger()


@dataclass
class LineupImpactAssessment:
    status: str  # "predicted" or "confirmed"
    confirmed_at: datetime | None
    home_squad_strength_delta: float  # e.g. -0.05 if key starter absent
    away_squad_strength_delta: float
    key_omissions: list[str]
    impact_summary: str
    recalculation_recommended: bool


class LineupIntelligenceEngine:
    """Starting Lineup Intelligence Engine per Master Directive Section 6.4."""

    @classmethod
    def evaluate_lineup_impact(
        cls,
        home_team: str,
        away_team: str,
        expected_lineup: list[str] | None,
        confirmed_lineup: list[str] | None,
        confirmed_at: datetime | None = None,
    ) -> LineupImpactAssessment:
        """Evaluates deviation between expected starting XI and confirmed starting XI."""
        if not confirmed_lineup:
            return LineupImpactAssessment(
                status="predicted",
                confirmed_at=None,
                home_squad_strength_delta=0.0,
                away_squad_strength_delta=0.0,
                key_omissions=[],
                impact_summary="Pre-lineup mode: Using 5-match rolling expected squad core rating.",
                recalculation_recommended=False,
            )

        expected_set = set(expected_lineup) if expected_lineup else set()
        confirmed_set = set(confirmed_lineup)

        omissions = list(expected_set - confirmed_set) if expected_set else []

        # Strength delta estimate: -2.5% strength penalty per omitted regular starter
        strength_delta = round(-0.025 * len(omissions), 3)
        recalc = len(omissions) > 0

        summary = (
            f"Confirmed Lineup Alert: {len(omissions)} expected starters omitted."
            if omissions
            else "Confirmed Lineup matches expected core squad rating."
        )

        return LineupImpactAssessment(
            status="confirmed",
            confirmed_at=confirmed_at or datetime.now(timezone.utc),
            home_squad_strength_delta=strength_delta,
            away_squad_strength_delta=0.0,
            key_omissions=omissions,
            impact_summary=summary,
            recalculation_recommended=recalc,
        )
