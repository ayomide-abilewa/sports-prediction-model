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
from backend.models.match import Match, MatchStatistics
from backend.models.team import Team


async def seed_live_matches():
    async with AsyncSessionLocal() as db:
        # Helper to get or create team
        async def get_or_create_team(name: str, country: str = "Europe") -> Team:
            t = await db.scalar(select(Team).where(Team.name == name))
            if not t:
                t = Team(name=name, canonical_name=name, country=country, current_elo=1600.0, aliases=[name])
                db.add(t)
                await db.flush()
            return t

        # Get Premier League, La Liga, Serie A, Bundesliga seasons
        epl_s = await db.scalar(select(Season).join(League).where(League.code == "ENG-Premier League"))
        esp_s = await db.scalar(select(Season).join(League).where(League.code == "ESP-La Liga"))
        ita_s = await db.scalar(select(Season).join(League).where(League.code == "ITA-Serie A"))
        ger_s = await db.scalar(select(Season).join(League).where(League.code == "GER-Bundesliga"))

        live_fixtures = [
            {
                "home": "Arsenal",
                "away": "Chelsea",
                "season": epl_s,
                "score_h": 1,
                "score_a": 0,
                "minute": 68,
                "stats_h": {"possession": 58.0, "shots": 14, "sot": 5, "corners": 6, "yellows": 1, "reds": 0},
                "stats_a": {"possession": 42.0, "shots": 7, "sot": 2, "corners": 3, "yellows": 2, "reds": 0},
            },
            {
                "home": "Barcelona",
                "away": "Real Madrid",
                "season": esp_s,
                "score_h": 2,
                "score_a": 1,
                "minute": 54,
                "stats_h": {"possession": 62.0, "shots": 16, "sot": 7, "corners": 7, "yellows": 2, "reds": 0},
                "stats_a": {"possession": 38.0, "shots": 9, "sot": 4, "corners": 3, "yellows": 3, "reds": 0},
            },
            {
                "home": "Inter",
                "away": "Juventus",
                "season": ita_s,
                "score_h": 0,
                "score_a": 0,
                "minute": 38,
                "stats_h": {"possession": 51.0, "shots": 8, "sot": 3, "corners": 4, "yellows": 1, "reds": 0},
                "stats_a": {"possession": 49.0, "shots": 6, "sot": 2, "corners": 2, "yellows": 1, "reds": 0},
            },
            {
                "home": "Bayern Munich",
                "away": "Borussia Dortmund",
                "season": ger_s,
                "score_h": 2,
                "score_a": 2,
                "minute": 76,
                "stats_h": {"possession": 55.0, "shots": 18, "sot": 8, "corners": 8, "yellows": 2, "reds": 0},
                "stats_a": {"possession": 45.0, "shots": 13, "sot": 6, "corners": 5, "yellows": 2, "reds": 0},
            },
        ]

        for item in live_fixtures:
            ht = await get_or_create_team(item["home"])
            at = await get_or_create_team(item["away"])

            # Check if live match exists
            m = await db.scalar(
                select(Match).where(
                    Match.home_team_id == ht.id,
                    Match.away_team_id == at.id,
                    Match.status == "in_play",
                )
            )

            if not m:
                m = Match(
                    season_id=item["season"].id if item["season"] else 1,
                    home_team_id=ht.id,
                    away_team_id=at.id,
                    kickoff=datetime.now(),
                    status="in_play",
                    ft_home_goals=item["score_h"],
                    ft_away_goals=item["score_a"],
                    ht_home_goals=1 if item["score_h"] > 0 else 0,
                    ht_away_goals=0,
                )
                db.add(m)
                await db.flush()

                # Add MatchStatistics
                db.add(
                    MatchStatistics(
                        match_id=m.id,
                        team_id=ht.id,
                        is_home=True,
                        possession=item["stats_h"]["possession"],
                        shots=item["stats_h"]["shots"],
                        shots_on_target=item["stats_h"]["sot"],
                        corners=item["stats_h"]["corners"],
                        yellow_cards=item["stats_h"]["yellows"],
                        red_cards=item["stats_h"]["reds"],
                    )
                )
                db.add(
                    MatchStatistics(
                        match_id=m.id,
                        team_id=at.id,
                        is_home=False,
                        possession=item["stats_a"]["possession"],
                        shots=item["stats_a"]["shots"],
                        shots_on_target=item["stats_a"]["sot"],
                        corners=item["stats_a"]["corners"],
                        yellow_cards=item["stats_a"]["yellows"],
                        red_cards=item["stats_a"]["reds"],
                    )
                )

        await db.commit()
        print("Successfully seeded 4 active live in-play blockbuster matches!")


if __name__ == "__main__":
    asyncio.run(seed_live_matches())
