from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Query
import pandas as pd
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.betting.confidence import ConfidenceClassifier
from backend.db.engine import get_db
from backend.models.league import Season
from backend.models.match import Match
from backend.models.odds import MarketOdds
from backend.probability.dixon_coles import DixonColesModel
from backend.probability.markets import MarketEngine

router = APIRouter(prefix="/predictions", tags=["Predictions"])
classifier = ConfidenceClassifier()


@router.get("")
async def list_predictions(
    league_code: str | None = Query(None),
    min_ev: float = Query(0.0, description="Minimum Expected Value e.g. 0.025 for +2.5%"),
    confidence_tier: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Calculates live probabilistic predictions, comparing model probabilities against available market odds."""
    # Fetch recent finished matches to fit model
    stmt = (
        select(Match)
        .options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.season).selectinload(Season.league),
            selectinload(Match.odds),
        )
        .where(Match.status == "finished")
        .order_by(desc(Match.kickoff))
        .limit(100)
    )
    res = await db.execute(stmt)
    matches = res.scalars().all()

    if not matches:
        return []

    # Fit Dixon-Coles on all matches
    df_data = [
        {
            "home_team": m.home_team.name,
            "away_team": m.away_team.name,
            "ft_home_goals": m.ft_home_goals,
            "ft_away_goals": m.ft_away_goals,
            "kickoff": m.kickoff,
        }
        for m in matches
    ]
    dc = DixonColesModel()
    try:
        dc.fit(pd.DataFrame(df_data))
    except Exception:
        return []

    results: list[dict[str, Any]] = []

    # Evaluate target matches
    for m in matches[:limit]:
        try:
            pred = dc.predict_match(m.home_team.name, m.away_team.name)
        except Exception:
            continue

        p_1x2 = pred["1x2"]
        p_ou25 = pred["totals"]["over_under_2.5"]

        # Find available odds
        odds_by_selection: dict[str, float] = {}
        for o in m.odds:
            odds_by_selection[f"{o.market_type}_{o.selection}"] = o.odds

        # Evaluate standard markets
        candidates = [
            ("1x2", "home", p_1x2["home"]),
            ("1x2", "draw", p_1x2["draw"]),
            ("1x2", "away", p_1x2["away"]),
            ("over_under_2.5", "over", p_ou25["over"]),
            ("over_under_2.5", "under", p_ou25["under"]),
        ]

        for m_type, sel, prob in candidates:
            key = f"{m_type}_{sel}"
            odds_val = odds_by_selection.get(key)
            if not odds_val or odds_val <= 1.0:
                continue

            eval_res = classifier.evaluate(prob, odds_val, quality_score=1.0)
            if eval_res.expected_value < min_ev:
                continue

            if confidence_tier and eval_res.tier != confidence_tier:
                continue

            results.append({
                "match_id": m.id,
                "fixture": f"{m.home_team.name} vs {m.away_team.name}",
                "league": m.season.league.name if m.season and m.season.league else "",
                "kickoff": m.kickoff.isoformat(),
                "market_type": m_type,
                "selection": sel,
                "model_probability": prob,
                "fair_odds": MarketEngine.calculate_fair_odds(prob),
                "available_odds": odds_val,
                "expected_value": eval_res.expected_value,
                "confidence_tier": eval_res.tier or "Unclassified",
                "is_value": eval_res.is_value,
            })

    return results
