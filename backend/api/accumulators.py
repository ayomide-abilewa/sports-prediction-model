from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import pandas as pd

from backend.betting.slip_combinator import CandidateLeg, SlipCombinator
from backend.db.engine import get_db
from backend.models.league import Season
from backend.models.match import Match
from backend.probability.dixon_coles import DixonColesModel

router = APIRouter(prefix="/accumulators", tags=["Accumulators"])


@router.get("")
async def generate_accumulators(
    category: str = Query("solid_core", description="banker_rollover, solid_core, sharp_multi, high_yield, corners_cards"),
    max_slips: int = Query(3, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Dynamically assembles and ranks multi-leg accumulator combinations according to Blueprint recipes."""
    # 1. Fetch recent matches to build model
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
        .limit(40)
    )
    res = await db.execute(stmt)
    matches = res.scalars().all()

    if not matches:
        return []

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

    # 2. Extract candidate legs
    candidates: list[CandidateLeg] = []
    for m in matches:
        try:
            pred = dc.predict_match(m.home_team.name, m.away_team.name)
        except Exception:
            continue

        p_1x2 = pred["1x2"]
        p_ou = pred["totals"]["over_under_2.5"]

        odds_map = {f"{o.market_type}_{o.selection}": o.odds for o in m.odds}

        market_options = [
            ("1x2", "home", p_1x2["home"]),
            ("1x2", "away", p_1x2["away"]),
            ("over_under_2.5", "over", p_ou["over"]),
            ("over_under_2.5", "under", p_ou["under"]),
        ]

        for m_type, sel, prob in market_options:
            key = f"{m_type}_{sel}"
            o_val = odds_map.get(key)
            if o_val and o_val > 1.10:
                ev = (prob * o_val) - 1.0
                candidates.append(
                    CandidateLeg(
                        prediction_id=m.id,
                        match_id=m.id,
                        league_code=m.season.league.code if m.season and m.season.league else "",
                        home_team=m.home_team.name,
                        away_team=m.away_team.name,
                        market_type=m_type,
                        selection=sel,
                        odds=o_val,
                        probability=prob,
                        expected_value=ev,
                    )
                )

    # 3. Generate candidate slips
    slips = SlipCombinator.generate_slips(candidates, category=category, max_results=max_slips)

    return [
        {
            "category": s.category,
            "slip_name": s.slip_name,
            "combined_odds": s.combined_odds,
            "joint_probability": s.joint_probability,
            "expected_return": s.expected_return,
            "risk_class": s.risk_class,
            "leg_count": len(s.legs),
            "legs": [
                {
                    "match_id": l.match_id,
                    "fixture": f"{l.home_team} vs {l.away_team}",
                    "market": l.market_type,
                    "selection": l.selection,
                    "odds": l.odds,
                    "probability": l.probability,
                    "expected_value": l.expected_value,
                }
                for l in s.legs
            ],
            "warnings": s.warnings,
        }
        for s in slips
    ]
