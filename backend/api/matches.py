from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.engine import get_db
from backend.models.league import Season
from backend.models.match import Match, MatchStatistics
from backend.models.odds import MarketOdds
from backend.models.team import Team
from backend.probability.dixon_coles import DixonColesModel
from backend.probability.markets import MarketEngine
import pandas as pd

router = APIRouter(prefix="/matches", tags=["Matches"])


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

    # Fetch recent matches for this league to fit Dixon-Coles dynamically
    season_id = match.season_id
    hist_stmt = (
        select(Match)
        .options(selectinload(Match.home_team), selectinload(Match.away_team))
        .where(Match.season_id == season_id, Match.status == "finished")
        .order_by(desc(Match.kickoff))
        .limit(380)
    )
    hist_res = await db.execute(hist_stmt)
    hist_matches = hist_res.scalars().all()

    model_prediction: dict[str, Any] | None = None
    if len(hist_matches) >= 30:
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
        "statistics": stats_data,
        "odds": odds_data,
        "model_analysis": model_prediction,
    }
