from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.betting.confidence import ConfidenceClassifier
from backend.db.engine import get_db
from backend.models.league import Season
from backend.models.match import Match, MatchStatistics
from backend.models.odds import MarketOdds
from backend.models.team import Team
from backend.probability.dixon_coles import DixonColesModel
from backend.probability.markets import MarketEngine
import pandas as pd

router = APIRouter(prefix="/matches", tags=["Matches"])
classifier = ConfidenceClassifier()


@router.get("/{match_id}")
async def get_match_detail(
    match_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves complete match details, statistics, odds, and probabilistic model outputs."""
    stmt = (
        select(Match)
        .options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.season).selectinload(Season.league),
            selectinload(Match.statistics),
            selectinload(Match.odds),
        )
        .where(Match.id == match_id)
    )

    res = await db.execute(stmt)
    match = res.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Fetch finished matches across DB to train Dixon-Coles
    hist_stmt = (
        select(Match)
        .options(selectinload(Match.home_team), selectinload(Match.away_team))
        .where(Match.status == "finished")
        .order_by(desc(Match.kickoff))
        .limit(200)
    )
    hist_res = await db.execute(hist_stmt)
    hist_matches = hist_res.scalars().all()

    model_prediction: dict[str, Any] | None = None
    surest_pick: dict[str, Any] | None = None
    ai_analysis_text = ""

    if len(hist_matches) >= 20:
        hist_records = [
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
            dc.fit(pd.DataFrame(hist_records))
            model_prediction = dc.predict_match(match.home_team.name, match.away_team.name)

            p_1x2 = model_prediction["1x2"]
            p_totals = model_prediction["totals"]
            p_btts = model_prediction["btts"]
            exp_goals = model_prediction["expected_goals"]

            # Pick candidates
            odds_map = {f"{o.market_type}_{o.selection}": o.odds for o in match.odds}
            picks = [
                {"market": "1X2", "selection": "Home Win", "prob": p_1x2["home"], "key": "1x2_home"},
                {"market": "1X2", "selection": "Draw", "prob": p_1x2["draw"], "key": "1x2_draw"},
                {"market": "1X2", "selection": "Away Win", "prob": p_1x2["away"], "key": "1x2_away"},
                {"market": "Goals", "selection": "Over 1.5 Goals", "prob": p_totals["over_under_1.5"]["over"], "key": "over_under_1.5_over"},
                {"market": "Goals", "selection": "Under 2.5 Goals", "prob": p_totals["over_under_2.5"]["under"], "key": "over_under_2.5_under"},
                {"market": "Goals", "selection": "Over 2.5 Goals", "prob": p_totals["over_under_2.5"]["over"], "key": "over_under_2.5_over"},
                {"market": "BTTS", "selection": "Both Teams to Score (Yes)", "prob": p_btts["yes"], "key": "btts_yes"},
            ]

            for p in picks:
                raw_o = odds_map.get(p["key"])
                p["fair_odds"] = MarketEngine.calculate_fair_odds(p["prob"])
                p["odds"] = raw_o if (raw_o and raw_o > 1.0) else round(p["fair_odds"] * 0.94, 2)
                p["ev"] = MarketEngine.calculate_expected_value(p["prob"], p["odds"])
                p["confidence_tier"] = "Tier 1 – Bankers" if p["prob"] >= 0.70 else ("Tier 2 – Solid Core" if p["prob"] >= 0.55 else "Sharp Value")

            # Surest pick is the highest probability selection
            picks.sort(key=lambda x: x["prob"], reverse=True)
            surest_pick = picks[0]

            # Construct tactical analysis narrative
            ai_analysis_text = (
                f"Statistical simulation projects a scoreline centered around {exp_goals['home']} for {match.home_team.name} "
                f"and {exp_goals['away']} for {match.away_team.name} (total expected goals: {exp_goals['total']}). "
                f"The highest conviction mathematical selection for this match is {surest_pick['selection']} ({surest_pick['market']}) "
                f"at {surest_pick['prob']*100:.1f}% estimated probability with available decimal odds of {surest_pick['odds']:.2f}."
            )
        except Exception:
            pass

    # Format odds
    odds_data = [
        {
            "market_type": o.market_type,
            "selection": o.selection,
            "odds": o.odds,
            "implied_prob": o.implied_prob,
        }
        for o in match.odds
    ]

    # Format stats
    stats_data = [
        {
            "is_home": s.is_home,
            "shots": s.shots,
            "shots_on_target": s.shots_on_target,
            "corners": s.corners,
            "fouls": s.fouls,
            "yellow_cards": s.yellow_cards,
            "red_cards": s.red_cards,
        }
        for s in match.statistics
    ]

    return {
        "id": match.id,
        "league": match.season.league.name if match.season and match.season.league else "",
        "season": match.season.season_code if match.season else "",
        "kickoff": match.kickoff.isoformat(),
        "status": match.status,
        "home_team": {
            "id": match.home_team.id,
            "name": match.home_team.name,
            "elo": match.home_team.current_elo,
        },
        "away_team": {
            "id": match.away_team.id,
            "name": match.away_team.name,
            "elo": match.away_team.current_elo,
        },
        "score": {
            "ft_home": match.ft_home_goals,
            "ft_away": match.ft_away_goals,
            "ht_home": match.ht_home_goals,
            "ht_away": match.ht_away_goals,
        },
        "surest_prediction": surest_pick,
        "ai_analysis": ai_analysis_text,
        "statistics": stats_data,
        "odds": odds_data,
        "model_analysis": model_prediction,
    }
