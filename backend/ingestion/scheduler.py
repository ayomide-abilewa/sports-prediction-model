from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.db.engine import AsyncSessionLocal
from backend.ingestion.base_adapter import IngestionResult
from backend.ingestion.football_data_uk import FootballDataUKAdapter
from backend.models.league import League, Season
from backend.models.match import Match, MatchStatistics
from backend.models.odds import Bookmaker, MarketOdds
from backend.models.system import DataSourceLog
from backend.models.team import Team

logger = structlog.get_logger()


class IngestionScheduler:
    """Coordinates and executes data ingestion across adapters and writes to the DB."""

    def __init__(self):
        self.fduk_adapter = FootballDataUKAdapter()

    async def get_or_create_team(self, session: AsyncSession, canonical_name: str, country: str = "") -> Team:
        """Finds or creates team by canonical name."""
        res = await session.execute(
            select(Team).where(Team.canonical_name == canonical_name)
        )
        team = res.scalar_one_or_none()
        if not team:
            team = Team(
                name=canonical_name,
                canonical_name=canonical_name,
                country=country,
                aliases=[],
                current_elo=1500.0,
            )
            session.add(team)
            await session.flush()
        return team

    async def get_or_create_season(self, session: AsyncSession, league: League, season_code: str) -> Season:
        """Finds or creates season record."""
        res = await session.execute(
            select(Season).where(
                Season.league_id == league.id,
                Season.season_code == season_code,
            )
        )
        season = res.scalar_one_or_none()
        if not season:
            season = Season(
                league_id=league.id,
                season_code=season_code,
                is_current=True,
            )
            session.add(season)
            await session.flush()
        return season

    async def get_bookmaker_cache(self, session: AsyncSession) -> dict[str, Bookmaker]:
        """Loads active bookmakers mapped by code."""
        res = await session.execute(select(Bookmaker))
        return {bm.code: bm for bm in res.scalars().all()}

    async def ingest_league_season(
        self, league_code: str, season_code: str
    ) -> IngestionResult:
        """Executes full pipeline for one league and season."""
        result = IngestionResult(
            source="football_data_uk",
            operation=f"ingest_{league_code}_{season_code}",
        )

        async with AsyncSessionLocal() as session:
            try:
                # 1. Fetch league from DB
                res = await session.execute(
                    select(League).where(League.code == league_code)
                )
                league = res.scalar_one_or_none()
                if not league:
                    result.errors.append(f"League code '{league_code}' not found in database")
                    result.complete("failed")
                    return result

                season = await self.get_or_create_season(session, league, season_code)
                bm_cache = await self.get_bookmaker_cache(session)

                # 2. Fetch raw match records from adapter
                records = await self.fduk_adapter.fetch_matches(league_code, season_code)
                result.records_processed = len(records)

                # 3. Process each match record
                for rec in records:
                    home_team = await self.get_or_create_team(session, rec["home_team"], league.country)
                    away_team = await self.get_or_create_team(session, rec["away_team"], league.country)

                    # Check for existing match
                    res_m = await session.execute(
                        select(Match).where(
                            Match.season_id == season.id,
                            Match.home_team_id == home_team.id,
                            Match.away_team_id == away_team.id,
                            Match.kickoff == rec["kickoff"],
                        )
                    )
                    match = res_m.scalar_one_or_none()

                    if match:
                        # Update scores if newly finished
                        if match.status != "finished" and rec["status"] == "finished":
                            match.ft_home_goals = rec["ft_home_goals"]
                            match.ft_away_goals = rec["ft_away_goals"]
                            match.ht_home_goals = rec["ht_home_goals"]
                            match.ht_away_goals = rec["ht_away_goals"]
                            match.status = "finished"
                            result.records_updated += 1
                        else:
                            result.records_skipped += 1
                    else:
                        match = Match(
                            season_id=season.id,
                            home_team_id=home_team.id,
                            away_team_id=away_team.id,
                            kickoff=rec["kickoff"],
                            status=rec["status"],
                            ft_home_goals=rec["ft_home_goals"],
                            ft_away_goals=rec["ft_away_goals"],
                            ht_home_goals=rec["ht_home_goals"],
                            ht_away_goals=rec["ht_away_goals"],
                            source=rec["source"],
                        )
                        session.add(match)
                        await session.flush()
                        result.records_new += 1

                        # Add team match statistics
                        for s_data in rec.get("stats", []):
                            team_id = home_team.id if s_data["is_home"] else away_team.id
                            stat = MatchStatistics(
                                match_id=match.id,
                                team_id=team_id,
                                is_home=s_data["is_home"],
                                shots=s_data.get("shots"),
                                shots_on_target=s_data.get("shots_on_target"),
                                corners=s_data.get("corners"),
                                fouls=s_data.get("fouls"),
                                yellow_cards=s_data.get("yellow_cards"),
                                red_cards=s_data.get("red_cards"),
                                source=rec["source"],
                            )
                            session.add(stat)

                        # Add odds records
                        for o_data in rec.get("odds", []):
                            bm = bm_cache.get(o_data["bookmaker_code"])
                            if bm:
                                odds_entry = MarketOdds(
                                    match_id=match.id,
                                    bookmaker_id=bm.id,
                                    market_type=o_data["market_type"],
                                    selection=o_data["selection"],
                                    odds=o_data["odds"],
                                    implied_prob=round(1.0 / o_data["odds"], 4) if o_data["odds"] > 0 else None,
                                    is_closing=True,
                                )
                                session.add(odds_entry)

                await session.commit()
                result.complete()

            except Exception as exc:
                await session.rollback()
                logger.error("ingestion_scheduler_error", error=str(exc))
                result.errors.append(str(exc))
                result.complete("failed")

            # Record Ingestion Log
            log_entry = DataSourceLog(
                source_name=result.source,
                operation=result.operation,
                status=result.status,
                records_processed=result.records_processed,
                records_new=result.records_new,
                records_updated=result.records_updated,
                error_message="; ".join(result.errors) if result.errors else None,
                duration_seconds=result.duration_seconds,
            )
            session.add(log_entry)
            await session.commit()

        return result
