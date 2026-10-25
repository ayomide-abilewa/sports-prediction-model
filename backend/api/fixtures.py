from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.engine import get_db
from backend.models.league import League, Season
from backend.models.match import Match
from backend.models.team import Team

router = APIRouter(prefix="/fixtures", tags=["Fixtures"])


@router.get("")
async def list_fixtures(
    league_code: str | None = Query(None, description="e.g. ENG-Premier League"),
    status: str | None = Query(None, description="scheduled, finished, in_play"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lists match fixtures with optional filtering by competition or status."""
    stmt = (
        select(Match)
        .options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.season).selectinload(Season.league),
        )
        .order_by(desc(Match.kickoff))
        .limit(limit)
    )

    if status:
        stmt = stmt.where(Match.status == status)

    if league_code:
        stmt = stmt.join(Match.season).join(Season.league).where(League.code == league_code)

    res = await db.execute(stmt)
    matches = res.scalars().all()

    return [
        {
            "id": m.id,
            "league": m.season.league.name if m.season and m.season.league else "Unknown",
            "league_code": m.season.league.code if m.season and m.season.league else "",
            "season": m.season.season_code if m.season else "",
            "kickoff": m.kickoff.isoformat(),
            "status": m.status,
            "home_team": m.home_team.name if m.home_team else "Unknown",
            "away_team": m.away_team.name if m.away_team else "Unknown",
            "ft_home_goals": m.ft_home_goals,
            "ft_away_goals": m.ft_away_goals,
            "ht_home_goals": m.ht_home_goals,
            "ht_away_goals": m.ht_away_goals,
        }
        for m in matches
    ]
