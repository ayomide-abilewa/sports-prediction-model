from __future__ import annotations

import asyncio
from datetime import datetime
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from backend.db.engine import AsyncSessionLocal
from backend.models.league import League, Season
from backend.models.match import Match
from backend.models.team import Team
from backend.models.odds import Bookmaker, MarketOdds


async def seed_european_cups():
    async with AsyncSessionLocal() as db:
        # 1. Ensure Bookmakers exist
        b365 = await db.scalar(select(Bookmaker).where(Bookmaker.code == "B365"))
        if not b365:
            b365 = Bookmaker(name="Bet365", code="B365", active=True)
            db.add(b365)
            await db.flush()

        sporty = await db.scalar(select(Bookmaker).where(Bookmaker.code == "SportyBet"))
        if not sporty:
            sporty = Bookmaker(name="SportyBet", code="SportyBet", active=True)
            db.add(sporty)
            await db.flush()

        # 2. Add or get leagues: UEFA Champions League & UEFA Europa League
        ucl = await db.scalar(select(League).where(League.code == "EUR-Champions League"))
        if not ucl:
            ucl = League(
                name="UEFA Champions League",
                country="Europe",
                code="EUR-Champions League",
                tier="A",
                data_coverage={"has_xg": True, "has_odds": True, "has_lineups": True},
                active=True,
            )
            db.add(ucl)
            await db.flush()

        uel = await db.scalar(select(League).where(League.code == "EUR-Europa League"))
        if not uel:
            uel = League(
                name="UEFA Europa League",
                country="Europe",
                code="EUR-Europa League",
                tier="A",
                data_coverage={"has_xg": True, "has_odds": True, "has_lineups": True},
                active=True,
            )
            db.add(uel)
            await db.flush()

        # Seasons
        ucl_s = await db.scalar(select(Season).where(Season.league_id == ucl.id, Season.season_code == "2425"))
        if not ucl_s:
            ucl_s = Season(league_id=ucl.id, season_code="2425", is_current=True)
            db.add(ucl_s)
            await db.flush()

        uel_s = await db.scalar(select(Season).where(Season.league_id == uel.id, Season.season_code == "2425"))
        if not uel_s:
            uel_s = Season(league_id=uel.id, season_code="2425", is_current=True)
            db.add(uel_s)
            await db.flush()

        # Helper to get or create team
        async def get_or_create_team(name: str) -> Team:
            t = await db.scalar(select(Team).where(Team.name == name))
            if not t:
                t = Team(name=name, canonical_name=name, country="Europe", current_elo=1550.0, aliases=[name])
                db.add(t)
                await db.flush()
            return t

        # UCL Fixtures
        ucl_fixtures = [
            ("Real Madrid", "Manchester City", "2026-10-27T20:00:00", {"h": 2.50, "d": 3.40, "a": 2.70, "o25": 1.65, "u25": 2.20}),
            ("Bayern Munich", "Paris Saint-Germain", "2026-10-27T20:00:00", {"h": 1.95, "d": 3.75, "a": 3.60, "o25": 1.55, "u25": 2.40}),
            ("Arsenal", "Inter", "2026-10-28T20:00:00", {"h": 1.85, "d": 3.50, "a": 4.20, "o25": 1.80, "u25": 2.00}),
            ("Barcelona", "Atalanta", "2026-10-28T20:00:00", {"h": 1.45, "d": 4.80, "a": 6.50, "o25": 1.40, "u25": 2.90}),
            ("Liverpool", "Bayer Leverkusen", "2026-10-28T20:00:00", {"h": 1.70, "d": 4.00, "a": 4.50, "o25": 1.50, "u25": 2.50}),
            ("Atletico Madrid", "Juventus", "2026-10-28T20:00:00", {"h": 2.10, "d": 3.20, "a": 3.60, "o25": 2.15, "u25": 1.68}),
            ("Borussia Dortmund", "Celtic", "2026-10-27T20:00:00", {"h": 1.50, "d": 4.50, "a": 5.80, "o25": 1.45, "u25": 2.70}),
            ("Aston Villa", "Bologna", "2026-10-27T20:00:00", {"h": 1.75, "d": 3.60, "a": 4.60, "o25": 1.85, "u25": 1.95}),
        ]

        # UEL Fixtures
        uel_fixtures = [
            ("Manchester United", "Porto", "2026-10-29T20:00:00", {"h": 2.30, "d": 3.35, "a": 3.10, "o25": 1.80, "u25": 2.00}),
            ("Tottenham", "Roma", "2026-10-29T20:00:00", {"h": 1.85, "d": 3.70, "a": 3.90, "o25": 1.60, "u25": 2.30}),
            ("Athletic Club", "AZ Alkmaar", "2026-10-29T20:00:00", {"h": 1.65, "d": 3.80, "a": 5.00, "o25": 1.75, "u25": 2.05}),
            ("Lyon", "Besiktas", "2026-10-29T20:00:00", {"h": 1.60, "d": 4.10, "a": 5.25, "o25": 1.60, "u25": 2.30}),
            ("Lazio", "Nice", "2026-10-29T20:00:00", {"h": 1.80, "d": 3.50, "a": 4.50, "o25": 1.95, "u25": 1.85}),
            ("Ajax", "Galatasaray", "2026-10-29T20:00:00", {"h": 2.15, "d": 3.50, "a": 3.20, "o25": 1.65, "u25": 2.20}),
            ("Real Sociedad", "Anderlecht", "2026-10-29T20:00:00", {"h": 1.55, "d": 4.00, "a": 6.00, "o25": 1.80, "u25": 2.00}),
        ]

        # Insert UCL matches
        for home_n, away_n, kickoff_str, odds_dict in ucl_fixtures:
            ht = await get_or_create_team(home_n)
            at = await get_or_create_team(away_n)
            kickoff = datetime.fromisoformat(kickoff_str)

            existing = await db.scalar(
                select(Match).where(
                    Match.home_team_id == ht.id,
                    Match.away_team_id == at.id,
                    Match.season_id == ucl_s.id,
                )
            )
            if not existing:
                match = Match(
                    season_id=ucl_s.id,
                    home_team_id=ht.id,
                    away_team_id=at.id,
                    kickoff=kickoff,
                    status="scheduled",
                )
                db.add(match)
                await db.flush()

                # Odds
                db.add(MarketOdds(match_id=match.id, bookmaker_id=b365.id, market_type="1x2", selection="home", odds=odds_dict["h"]))
                db.add(MarketOdds(match_id=match.id, bookmaker_id=b365.id, market_type="1x2", selection="draw", odds=odds_dict["d"]))
                db.add(MarketOdds(match_id=match.id, bookmaker_id=b365.id, market_type="1x2", selection="away", odds=odds_dict["a"]))
                db.add(MarketOdds(match_id=match.id, bookmaker_id=b365.id, market_type="over_under_2.5", selection="over", odds=odds_dict["o25"]))
                db.add(MarketOdds(match_id=match.id, bookmaker_id=b365.id, market_type="over_under_2.5", selection="under", odds=odds_dict["u25"]))

        # Insert UEL matches
        for home_n, away_n, kickoff_str, odds_dict in uel_fixtures:
            ht = await get_or_create_team(home_n)
            at = await get_or_create_team(away_n)
            kickoff = datetime.fromisoformat(kickoff_str)

            existing = await db.scalar(
                select(Match).where(
                    Match.home_team_id == ht.id,
                    Match.away_team_id == at.id,
                    Match.season_id == uel_s.id,
                )
            )
            if not existing:
                match = Match(
                    season_id=uel_s.id,
                    home_team_id=ht.id,
                    away_team_id=at.id,
                    kickoff=kickoff,
                    status="scheduled",
                )
                db.add(match)
                await db.flush()

                # Odds
                db.add(MarketOdds(match_id=match.id, bookmaker_id=b365.id, market_type="1x2", selection="home", odds=odds_dict["h"]))
                db.add(MarketOdds(match_id=match.id, bookmaker_id=b365.id, market_type="1x2", selection="draw", odds=odds_dict["d"]))
                db.add(MarketOdds(match_id=match.id, bookmaker_id=b365.id, market_type="1x2", selection="away", odds=odds_dict["a"]))
                db.add(MarketOdds(match_id=match.id, bookmaker_id=b365.id, market_type="over_under_2.5", selection="over", odds=odds_dict["o25"]))
                db.add(MarketOdds(match_id=match.id, bookmaker_id=b365.id, market_type="over_under_2.5", selection="under", odds=odds_dict["u25"]))

        await db.commit()
        print("Successfully seeded UEFA Champions League and UEFA Europa League fixtures!")


if __name__ == "__main__":
    asyncio.run(seed_european_cups())
