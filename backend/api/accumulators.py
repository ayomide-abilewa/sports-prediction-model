from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
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
from backend.ingestion.sportybet_service import (
    fetch_sporty_upcoming_events,
    generate_real_sportybet_booking_code,
    resolve_sportybet_booking_selections,
)
from backend.api.predictions import _build_sporty_match_item, _get_fitted_model
from backend.services.sportybet_persistence import clear_sporty_fixture_carry, save_sporty_fixture

router = APIRouter(prefix="/accumulators", tags=["Accumulators"])


def _league_priority(name: str) -> int:
    league = name.casefold()
    priorities = (
        ("premier league", 0), ("la liga", 1), ("laliga", 1), ("primera division", 1),
        ("bundesliga", 2), ("brasileiro", 12), ("serie a", 3), ("ligue 1", 4),
        ("champions league", 5), ("europa league", 6),
        ("conference league", 7), ("championship", 8),
        ("eredivisie", 9), ("primeira liga", 10), ("mls", 11),
    )
    return next((rank for token, rank in priorities if token in league), 20)


@router.get("/daily")
async def generate_daily_accumulator_card(
    max_matches: int = Query(30, ge=1, le=30),
    match_date: str | None = Query(None, alias="date", description="Local calendar date YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Builds a daily pick card from current feed events, without fabricated odds or props."""
    try:
        target_date = datetime.fromisoformat(match_date).date() if match_date else datetime.now(ZoneInfo("Africa/Lagos")).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must use YYYY-MM-DD")

    dc = await _get_fitted_model(db)
    now = datetime.now(timezone.utc)
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in await asyncio.to_thread(fetch_sporty_upcoming_events):
        item = _build_sporty_match_item(event, dc)
        if not item:
            continue
        kickoff = datetime.fromisoformat(item["kickoff"].replace("Z", "+00:00"))
        if kickoff <= now or kickoff.astimezone(ZoneInfo("Africa/Lagos")).date() != target_date:
            continue
        identity = str(event.get("eventId"))
        if identity in seen:
            continue
        seen.add(identity)
        markets = item.get("markets", [])
        markets = [
            market for market in markets
            if 1.0 < market.get("odds", 0) <= 10.0
            and 0.0 < market.get("probability", 0) < 1.0
        ]
        if not markets:
            continue
        model_value = [
            market for market in markets
            if market.get("probability_source") == "model"
            and market.get("ev") is not None and market["ev"] > 0
        ]
        # Expected value from market-implied probabilities is not independent
        # evidence of an edge; use the best consensus probability as fallback.
        pool = model_value or markets
        pick = max(pool, key=lambda market: (
            market.get("probability", 0),
            market.get("ev", -1) if market.get("probability_source") == "model" else -1,
            -market.get("odds", 99),
        ))
        persisted_market = {
            key: pick.get(key)
            for key in (
                "market", "selection", "odds", "probability", "ev", "confidence_tier",
                "probability_source", "event_id", "market_id", "outcome_id", "specifier",
            )
        }
        candidates.append({
            "match_id": None,
            "event_id": pick.get("event_id"),
            "market_id": pick.get("market_id"),
            "outcome_id": pick.get("outcome_id"),
            "specifier": pick.get("specifier"),
            "fixture": item["fixture"],
            "league": item["league"],
            "kickoff": item["kickoff"],
            "market": pick["market"],
            "selection": pick["selection"],
            "odds": pick["odds"],
            "probability": pick["probability"],
            "probability_source": pick.get("probability_source", "market"),
            "expected_value": pick.get("ev"),
            "rationale": pick.get("rationale"),
            "_event": event,
            "_item": item,
            "_market": persisted_market,
        })
    candidates.sort(key=lambda leg: (
        _league_priority(leg["league"]),
        leg["probability_source"] != "model",
        -leg["probability"],
        leg["kickoff"],
    ))
    legs = candidates[:max_matches]
    selected_ids = {leg["event_id"] for leg in legs}
    for candidate in candidates:
        if candidate["event_id"] not in selected_ids:
            await clear_sporty_fixture_carry(db, candidate["_event"])
    for leg in legs:
        item = leg.pop("_item")
        event = leg.pop("_event")
        persisted_market = leg.pop("_market")
        leg["match_id"] = await save_sporty_fixture(db, event, {**item, "markets": [persisted_market]})
    combined_odds = 1.0
    joint_probability = 1.0
    for leg in legs:
        combined_odds *= leg["odds"]
        joint_probability *= leg["probability"]
    return {
        "date": target_date.isoformat(),
        "provider": "SportyBet live football feed",
        "available_matches": len(candidates),
        "leg_count": len(legs),
        "combined_odds": round(combined_odds, 2),
        "joint_probability": joint_probability,
        "warnings": [
            "A long accumulator has a very low chance of winning; the displayed joint probability assumes independent legs.",
            "Market-sourced probabilities reflect bookmaker prices after margin removal; model-sourced probabilities are uncalibrated forecasts.",
        ],
        "legs": legs,
    }


class CustomSlipLegRequest(BaseModel):
    match_id: int
    fixture: str
    market: str
    selection: str
    odds: float
    probability: float
    event_id: str | None = None
    market_id: str | None = None
    outcome_id: str | None = None
    specifier: str | None = None
    kickoff: str | None = None


class CustomSlipRequest(BaseModel):
    slip_name: str = "Custom Custom Accumulator"
    legs: list[CustomSlipLegRequest]


@router.post("/custom")
async def build_custom_slip(payload: CustomSlipRequest) -> dict[str, Any]:
    """Books user selections with SportyBet and returns its official share code."""
    if not payload.legs:
        raise HTTPException(status_code=400, detail="Cannot create slip with 0 legs")

    leg_data = [leg.model_dump() for leg in payload.legs]
    sporty_selections = []
    legs_without_sporty_ids = []
    joint_prob = 1.0
    for leg in payload.legs:
        joint_prob *= max(leg.probability, 0.05)
        if leg.event_id and leg.market_id and leg.outcome_id:
            sporty_selections.append({
                "eventId": leg.event_id,
                "marketId": leg.market_id,
                "outcomeId": leg.outcome_id,
                "specifier": leg.specifier,
            })
        else:
            legs_without_sporty_ids.append(leg.fixture)

    if legs_without_sporty_ids:
        sporty_selections, unresolved_fixtures = await asyncio.to_thread(
            resolve_sportybet_booking_selections, leg_data
        )
        if unresolved_fixtures:
            legs_without_sporty_ids = unresolved_fixtures
        else:
            legs_without_sporty_ids = []

    if legs_without_sporty_ids:
        raise HTTPException(
            status_code=422,
            detail=(
                "SportyBet could not confirm these exact fixture and market selections. "
                "Choose current picks from Match Centre or remove them: " + ", ".join(legs_without_sporty_ids)
            ),
        )

    combined_odds = 1.0
    for leg, resolved in zip(payload.legs, leg_data):
        leg.event_id = resolved.get("event_id")
        leg.market_id = resolved.get("market_id")
        leg.outcome_id = resolved.get("outcome_id")
        leg.specifier = resolved.get("specifier")
        leg.odds = resolved.get("odds", leg.odds)
        combined_odds *= max(leg.odds, 1.01)

    combined_odds = round(combined_odds, 2)
    joint_prob = round(joint_prob, 4)
    exp_return = round((combined_odds * joint_prob) - 1.0, 4)

    # Attempt to book directly via SportyBet official API
    sporty_res = await asyncio.to_thread(generate_real_sportybet_booking_code, sporty_selections)
    if not sporty_res.get("success") or not sporty_res.get("share_code"):
        detail = sporty_res.get("message") or sporty_res.get("error") or "SportyBet did not return a booking code."
        raise HTTPException(status_code=502, detail=f"Could not create SportyBet booking code: {detail}")
    booking_code = sporty_res["share_code"]
    share_url = sporty_res.get("share_url") or f"https://www.sportybet.com/ng/?shareCode={booking_code}"

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
        "share_url": share_url,
        "is_official_sporty": True,
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

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    target_stmt = target_stmt.where(Match.status == "scheduled", Match.kickoff >= now).order_by(asc(Match.kickoff))

    target_stmt = target_stmt.limit(60)
    target_res = await db.execute(target_stmt)
    matches = target_res.scalars().all()

    # 3. Extract candidate legs
    candidates: list[CandidateLeg] = []
    for m in matches:
        if m.home_team.name not in dc.team_idx or m.away_team.name not in dc.team_idx:
            continue
        try:
            pred = dc.predict_match(m.home_team.name, m.away_team.name)
        except Exception:
            continue

        p_1x2 = pred.get("1x2", {})
        p_dc = pred.get("double_chance", {})
        p_ou = pred.get("totals", {}).get("over_under_2.5", {})
        p_ou15 = pred.get("totals", {}).get("over_under_1.5", {})
        p_btts = pred.get("btts", {})

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
        ]

        for m_type, sel, prob in market_options:
            key = f"{m_type}_{sel}"
            raw_odds = odds_map.get(key)
            if not raw_odds or raw_odds <= 1.05:
                continue
            o_val = raw_odds
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
                    kickoff=m.kickoff.isoformat(),
                )
            )

    # 4. Generate candidate slips
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
                    "kickoff": l.kickoff,
                }
                for l in s.legs
            ],
            "warnings": s.warnings,
        }
        for s in slips
    ]
