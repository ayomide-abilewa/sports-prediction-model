from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import structlog

logger = structlog.get_logger()


@dataclass
class CorrelationCheckResult:
    is_valid: bool
    warning: str | None
    correlation_factor: float = 1.0


class CorrelationEngine:
    """Detects dependent selections in accumulators and adjusts joint probabilities."""

    # Pre-calculated correlation factors for common same-match market combinations
    SAME_MATCH_CORRELATIONS: dict[tuple[str, str], float] = {
        # BTTS Yes + Over 2.5 has strong positive correlation
        ("btts_yes", "over_2.5"): 0.85,
        ("btts_no", "under_2.5"): 0.88,
        # Home Win + Over 2.5 has moderate positive correlation
        ("home_win", "over_2.5"): 0.80,
        ("away_win", "over_2.5"): 0.80,
    }

    @classmethod
    def check_leg_pair(
        cls,
        match_id_1: int,
        market_1: str,
        selection_1: str,
        match_id_2: int,
        market_2: str,
        selection_2: str,
    ) -> CorrelationCheckResult:
        """Verifies if two legs conflict or exhibit dependencies."""
        if match_id_1 != match_id_2:
            # Independent matches from different fixtures
            return CorrelationCheckResult(is_valid=True, warning=None, correlation_factor=1.0)

        # Same match: check for conflicting or duplicate selections
        if market_1 == market_2:
            return CorrelationCheckResult(
                is_valid=False,
                warning=f"Duplicate market '{market_1}' in same match {match_id_1}",
                correlation_factor=0.0,
            )

        key1 = f"{selection_1}_{market_1}".lower()
        key2 = f"{selection_2}_{market_2}".lower()
        factor = cls.SAME_MATCH_CORRELATIONS.get((key1, key2)) or cls.SAME_MATCH_CORRELATIONS.get((key2, key1))

        if factor is not None:
            return CorrelationCheckResult(
                is_valid=True,
                warning="Same-match correlated leg detected",
                correlation_factor=factor,
            )

        # By default, disallow multiple unhandled selections on the same match
        return CorrelationCheckResult(
            is_valid=False,
            warning=f"Unmodeled multi-selection on same match {match_id_1}",
            correlation_factor=0.0,
        )
