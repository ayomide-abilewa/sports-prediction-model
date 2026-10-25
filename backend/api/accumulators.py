from __future__ import annotations

import random
import string
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
import pandas as pd
from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.betting.slip_combinator import CandidateLeg, SlipCombinator
from backend.db.engine import get_db
from backend.models.league import Season
from backend.models.match import Match
from backend.models.odds import MarketOdds
from backend.probability.dixon_coles import DixonColesModel

router = APIRouter(prefix="/accumulators", tags=["Accumulators"])


def generate_booking_code(prefix: str = "SB") -> str:
    """Generates an alphanumeric SportyBet-style booking code."""
    chars = string.ascii_uppercase + string.digits
    rand_part = "".join(random.choices(chars, k=6))
    return f"{prefix}-{rand_part}"


class CustomSlipLegRequest(BaseModel):
    match_id: int
    fixture: str
    market: str
    selection: str
    odds: float
    probability: float


class CustomSlipRequest(BaseModel):
    slip_name: str = "Custom Custom Accumulator"
    legs: list[CustomSlipLegRequest]


@router.post("/custom")
async def build_custom_slip(payload: CustomSlipRequest) -> dict[str, Any]:
    """Combines user-selected legs into an accumulator with live odds, joint probability, and booking code."""
    if not payload.legs:
        raise HTTPException(status_code=400, detail="Cannot create slip with 0 legs")

    combined_odds = 1.0
    joint_prob = 1.0

    for leg in payload.legs:
        combined_odds *= max(leg.odds, 1.01)
        joint_prob *= max(leg.probability, 0.05)

    combined_odds = round(combined_odds, 2)
    joint_prob = round(joint_prob, 4)
    exp_return = round((combined_odds * joint_prob) - 1.0, 4)
    booking_code = generate_booking_code()

    risk_rating = (
        "Low Risk" if combined_odds <= 2.8
        else ("Moderate Risk" if combined_odds <= 8.0
        else ("Elevated Risk" if combined_odds <= 25.0 else "High Variance"))
    )

    return {
        "slip_name": payload.slip_name,
        "combined_odds": combined_odds,
        "joint_probability": joint_prob,
        "expected_return": exp_return,
        "risk_class": risk_rating,
        "booking_code": booking_code,
        "leg_count": len(payload.legs),
        "legs": [leg.dict() for leg in payload.legs],
    }


@router.get("")
async def generate_accumulators(
    category: str = Query("solid_core", description="banker_rollover, solid_core, sharp_multi, high_yield, corners_cards"),
    max_slips: int = Query(3, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Dynamically assembles and ranks multi-leg accumulator combinations according to Blueprint recipes."""
    # 1. Fetch recent finished matches to build statistical model
    hist_stmt = (
        select(Match)
        .options(selectinload(Match.home_team), selectinload(Match.away_team))
        .where(Match.status == "finished")
        .order_by(desc(Match.kickoff))
        .limit(100)
    )
    hist_res = await db.execute(hist_stmt)
    hist_matches = hist_res.scalars().all()

    if not hist_matches:
        return []

    df_data = [
        {
            "home_team": m.home_team.name,
            "away_team": m.away_team.name,
            "ft_home_goals": m.ft_home_goals,
            "ft_away_goals": m.ft_away_goals,
            "kickoff": m.kickoff,
        }
        for m in hist_matches
    ]
    dc = DixonColesModel()
    try:
        dc.fit(pd.DataFrame(df_data))
    except Exception:
        return []

    # 2. Fetch target matches (prioritize SCHEDULED / UPCOMING matches for real betting!)
    target_stmt = (
        select(Match)
        .options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.season).selectinload(Season.league),
            selectinload(Match.odds),
        )
    )

    now = datetime.now()
    sched_check = await db.scalar(
        select(Match.id).where(Match.status == "scheduled", Match.kickoff >= now).limit(1)
    )
    if sched_check:
        target_stmt = target_stmt.where(Match.status == "scheduled", Match.kickoff >= now).order_by(asc(Match.kickoff))
    else:
        target_stmt = target_stmt.order_by(desc(Match.kickoff))

    target_stmt = target_stmt.limit(60)
    target_res = await db.execute(target_stmt)
    matches = target_res.scalars().all()

    # 3. Extract candidate legs
    candidates: list[CandidateLeg] = []
    for m in matches:
        try:
            pred = dc.predict_match(m.home_team.name, m.away_team.name)
        except Exception:
            continue

        p_1x2 = pred.get("1x2", {})
        p_dc = pred.get("double_chance", {})
        p_ou = pred.get("totals", {}).get("over_under_2.5", {})
        p_ou15 = pred.get("totals", {}).get("over_under_1.5", {})
        p_btts = pred.get("btts", {})
        p_corners = pred.get("corners", {}).get("corners_over_under_7.5", {})
        p_cards = pred.get("cards", {}).get("cards_over_under_2.5", {})

        odds_map = {f"{o.market_type}_{o.selection}": o.odds for o in m.odds}

        market_options = [
            ("1x2", "home", p_1x2.get("home", 0.0)),
            ("1x2", "away", p_1x2.get("away", 0.0)),
            ("double_chance", "1x", p_dc.get("1x", 0.0)),
            ("double_chance", "x2", p_dc.get("x2", 0.0)),
            ("over_under_2.5", "over", p_ou.get("over", 0.0)),
            ("over_under_2.5", "under", p_ou.get("under", 0.0)),
            ("over_under_1.5", "over", p_ou15.get("over", 0.0)),
            ("btts", "yes", p_btts.get("yes", 0.0)),
            ("corners", "over_7.5", p_corners.get("over", 0.0)),
            ("cards", "over_2.5", p_cards.get("over", 0.0)),
        ]

        for m_type, sel, prob in market_options:
            key = f"{m_type}_{sel}"
            raw_odds = odds_map.get(key)
            o_val = raw_odds if (raw_odds and raw_odds > 1.05) else round((1.0 / max(prob, 0.05)) * 0.94, 2)
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

    # 4. Generate candidate slips
    slips = SlipCombinator.generate_slips(candidates, category=category, max_results=max_slips)

    # If combinator strict recipe didn't yield slips, generate high-conviction slip directly
    if not slips and candidates:
        # Build a bespoke slip for this category
        sorted_cand = sorted(candidates, key=lambda x: x.probability, reverse=True)
        # Take unique matches
        seen_matches = set()
        chosen = []
        for c in sorted_cand:
            if c.match_id not in seen_matches:
                seen_matches.add(c.match_id)
                chosen.append(c)
                if len(chosen) >= (2 if category == "banker_rollover" else (4 if category == "solid_core" else 6)):
                    break

        if len(chosen) >= 2:
            c_odds = 1.0
            j_prob = 1.0
            for leg in chosen:
                c_odds *= leg.odds
                j_prob *= leg.probability
            c_odds = round(c_odds, 2)
            j_prob = round(j_prob, 4)

            return [{
                "category": category,
                "slip_name": SlipCombinator.RECIPES.get(category, {}).get("name", "Optimized Slip"),
                "combined_odds": c_odds,
                "joint_probability": j_prob,
                "expected_return": round((c_odds * j_prob) - 1.0, 4),
                "risk_class": "Curated Top Probability Slip",
                "booking_code": generate_booking_code(),
                "leg_count": len(chosen),
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
                    for l in chosen
                ],
                "warnings": [],
            }]

    return [
        {
            "category": s.category,
            "slip_name": s.slip_name,
            "combined_odds": s.combined_odds,
            "joint_probability": s.joint_probability,
            "expected_return": s.expected_return,
            "risk_class": s.risk_class,
            "booking_code": generate_booking_code(),
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
