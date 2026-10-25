from __future__ import annotations

import asyncio
from backend.db.engine import AsyncSessionLocal, init_db
from backend.models.league import League
from backend.models.odds import Bookmaker
from sqlalchemy import select
import structlog

logger = structlog.get_logger()

# Default Leagues configuration per Master Directive Section 4.1
DEFAULT_LEAGUES = [
    # Tier A – Advanced statistical coverage
    {
        "name": "Premier League",
        "country": "England",
        "code": "ENG-Premier League",
        "tier": "A",
        "data_coverage": {
            "fduk_code": "E0",
            "has_xg": True,
            "has_odds": True,
            "has_lineups": True,
            "has_player_stats": True,
        },
    },
    {
        "name": "La Liga",
        "country": "Spain",
        "code": "ESP-La Liga",
        "tier": "A",
        "data_coverage": {
            "fduk_code": "SP1",
            "has_xg": True,
            "has_odds": True,
            "has_lineups": True,
            "has_player_stats": True,
        },
    },
    {
        "name": "Serie A",
        "country": "Italy",
        "code": "ITA-Serie A",
        "tier": "A",
        "data_coverage": {
            "fduk_code": "I1",
            "has_xg": True,
            "has_odds": True,
            "has_lineups": True,
            "has_player_stats": True,
        },
    },
    {
        "name": "Bundesliga",
        "country": "Germany",
        "code": "GER-Bundesliga",
        "tier": "A",
        "data_coverage": {
            "fduk_code": "D1",
            "has_xg": True,
            "has_odds": True,
            "has_lineups": True,
            "has_player_stats": True,
        },
    },
    {
        "name": "Ligue 1",
        "country": "France",
        "code": "FRA-Ligue 1",
        "tier": "A",
        "data_coverage": {
            "fduk_code": "F1",
            "has_xg": True,
            "has_odds": True,
            "has_lineups": True,
            "has_player_stats": True,
        },
    },
    {
        "name": "Eredivisie",
        "country": "Netherlands",
        "code": "NLD-Eredivisie",
        "tier": "A",
        "data_coverage": {
            "fduk_code": "N1",
            "has_xg": False,
            "has_odds": True,
            "has_lineups": True,
            "has_player_stats": True,
        },
    },
    {
        "name": "Championship",
        "country": "England",
        "code": "ENG-Championship",
        "tier": "A",
        "data_coverage": {
            "fduk_code": "E1",
            "has_xg": False,
            "has_odds": True,
            "has_lineups": True,
            "has_player_stats": True,
        },
    },
    # Tier B – Team-level statistical coverage
    {
        "name": "Primeira Liga",
        "country": "Portugal",
        "code": "PRT-Primeira Liga",
        "tier": "B",
        "data_coverage": {
            "fduk_code": "P1",
            "has_xg": False,
            "has_odds": True,
            "has_lineups": False,
            "has_player_stats": True,
        },
    },
    {
        "name": "Belgian Pro League",
        "country": "Belgium",
        "code": "BEL-Pro League",
        "tier": "B",
        "data_coverage": {
            "fduk_code": "B1",
            "has_xg": False,
            "has_odds": True,
            "has_lineups": False,
            "has_player_stats": False,
        },
    },
    {
        "name": "Super Lig",
        "country": "Turkey",
        "code": "TUR-Super Lig",
        "tier": "B",
        "data_coverage": {
            "fduk_code": "T1",
            "has_xg": False,
            "has_odds": True,
            "has_lineups": False,
            "has_player_stats": False,
        },
    },
    {
        "name": "Scottish Premiership",
        "country": "Scotland",
        "code": "SCO-Premiership",
        "tier": "B",
        "data_coverage": {
            "fduk_code": "SC0",
            "has_xg": False,
            "has_odds": True,
            "has_lineups": False,
            "has_player_stats": False,
        },
    },
]

# Supported Bookmakers
DEFAULT_BOOKMAKERS = [
    {"name": "Pinnacle Sports", "code": "PS", "active": True},
    {"name": "Bet365", "code": "B365", "active": True},
    {"name": "Market Average", "code": "Avg", "active": True},
    {"name": "Market Maximum", "code": "Max", "active": True},
    {"name": "William Hill", "code": "WH", "active": True},
    {"name": "SportyBet Nigeria", "code": "SPORTYBET", "active": True},
]


async def seed_initial_data() -> None:
    """Seed initial leagues and bookmakers if they don't already exist."""
    await init_db()

    async with AsyncSessionLocal() as session:
        # Seed Leagues
        for l_data in DEFAULT_LEAGUES:
            result = await session.execute(
                select(League).where(League.code == l_data["code"])
            )
            existing = result.scalar_one_or_none()
            if not existing:
                league = League(
                    name=l_data["name"],
                    country=l_data["country"],
                    code=l_data["code"],
                    tier=l_data["tier"],
                    data_coverage=l_data["data_coverage"],
                    active=True,
                )
                session.add(league)

        # Seed Bookmakers
        for b_data in DEFAULT_BOOKMAKERS:
            result = await session.execute(
                select(Bookmaker).where(Bookmaker.code == b_data["code"])
            )
            existing = result.scalar_one_or_none()
            if not existing:
                bm = Bookmaker(
                    name=b_data["name"],
                    code=b_data["code"],
                    active=b_data["active"],
                )
                session.add(bm)

        await session.commit()
        print("Successfully seeded initial leagues and bookmakers.")


if __name__ == "__main__":
    asyncio.run(seed_initial_data())
