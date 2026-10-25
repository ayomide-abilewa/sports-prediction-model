from __future__ import annotations

import io
from datetime import datetime
from typing import Any
import httpx
import numpy as np
import pandas as pd
import structlog
from backend.config import settings
from backend.ingestion.base_adapter import BaseAdapter, IngestionResult
from backend.ingestion.team_mapper import team_mapper
from backend.ingestion.validation import data_validator

logger = structlog.get_logger()


class FootballDataUKAdapter(BaseAdapter):
    """Adapter for downloading and parsing historical match data and betting odds
    from Football-Data.co.uk CSV distributions.
    """

    # League name/code mapping to Football-Data.co.uk file prefixes
    LEAGUE_MAP: dict[str, str] = {
        "ENG-Premier League": "E0",
        "ENG-Championship": "E1",
        "ESP-La Liga": "SP1",
        "ITA-Serie A": "I1",
        "GER-Bundesliga": "D1",
        "FRA-Ligue 1": "F1",
        "NLD-Eredivisie": "N1",
        "BEL-Pro League": "B1",
        "PRT-Primeira Liga": "P1",
        "TUR-Super Lig": "T1",
        "SCO-Premiership": "SC0",
    }

    @property
    def source_name(self) -> str:
        return "football_data_uk"

    def build_csv_url(self, league_code: str, season: str) -> str:
        """Constructs target CSV download URL.
        
        Args:
            league_code: e.g. "ENG-Premier League" or "E0"
            season: 4-digit code e.g. "2425" or "2324"
        """
        prefix = self.LEAGUE_MAP.get(league_code, league_code)
        clean_season = season.replace("/", "").replace("-", "")
        if len(clean_season) == 4 and clean_season.startswith("20"):
            # e.g. "2024" -> "2425"
            yr = int(clean_season[-2:])
            clean_season = f"{yr:02d}{yr+1:02d}"
        return f"{settings.fduk_base_url}/mmz4281/{clean_season}/{prefix}.csv"

    async def health_check(self) -> bool:
        """Verify Football-Data.co.uk accessibility."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.head(settings.fduk_base_url)
                return resp.status_code < 400
        except Exception as exc:
            logger.warning("fduk_health_check_failed", error=str(exc))
            return False

    @staticmethod
    def parse_kickoff_datetime(date_str: Any, time_str: Any = None) -> datetime:
        """Parses mixed date formats (DD/MM/YYYY or DD/MM/YY) and optional time."""
        if not date_str or pd.isna(date_str):
            return datetime.utcnow()

        d_str = str(date_str).strip()
        t_str = str(time_str).strip() if (time_str and not pd.isna(time_str)) else "15:00"

        # Try multiple date formats
        for d_fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
            for t_fmt in ("%H:%M", "%H:%M:%S"):
                try:
                    return datetime.strptime(f"{d_str} {t_str}", f"{d_fmt} {t_fmt}")
                except ValueError:
                    pass
            try:
                dt = datetime.strptime(d_str, d_fmt)
                return dt.replace(hour=15, minute=0)
            except ValueError:
                pass

        logger.warning("date_parsing_fallback", raw_date=date_str)
        return datetime.utcnow()

    async def fetch_csv_content(self, url: str) -> str:
        """Downloads raw CSV bytes via HTTP."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            # Try utf-8, fallback to latin-1
            try:
                return resp.content.decode("utf-8")
            except UnicodeDecodeError:
                return resp.content.decode("latin-1")

    async def fetch_matches(self, league_code: str, season: str) -> list[dict[str, Any]]:
        """Downloads and normalizes match records, team statistics, and betting odds."""
        url = self.build_csv_url(league_code, season)
        logger.info("fetching_fduk_csv", league=league_code, season=season, url=url)

        try:
            content = await self.fetch_csv_content(url)
        except Exception as exc:
            logger.error("fduk_fetch_error", url=url, error=str(exc))
            return []

        df = pd.read_csv(io.StringIO(content))
        # Filter out trailing empty rows
        if "HomeTeam" in df.columns:
            df = df.dropna(subset=["HomeTeam", "AwayTeam"])
        else:
            logger.error("fduk_invalid_columns", columns=list(df.columns))
            return []

        records: list[dict[str, Any]] = []

        for _, row in df.iterrows():
            raw_home = str(row.get("HomeTeam", "")).strip()
            raw_away = str(row.get("AwayTeam", "")).strip()
            if not raw_home or not raw_away:
                continue

            home_team, _ = team_mapper.resolve(raw_home)
            away_team, _ = team_mapper.resolve(raw_away)

            kickoff = self.parse_kickoff_datetime(
                row.get("Date"), row.get("Time")
            )

            # Goals
            fthg = int(row["FTHG"]) if pd.notna(row.get("FTHG")) else None
            ftag = int(row["FTAG"]) if pd.notna(row.get("FTAG")) else None
            hthg = int(row["HTHG"]) if pd.notna(row.get("HTHG")) else None
            htag = int(row["HTAG"]) if pd.notna(row.get("HTAG")) else None

            status = "finished" if fthg is not None and ftag is not None else "scheduled"

            # Match statistics
            home_stats = {
                "team_name": home_team,
                "is_home": True,
                "shots": int(row["HS"]) if pd.notna(row.get("HS")) else None,
                "shots_on_target": int(row["HST"]) if pd.notna(row.get("HST")) else None,
                "corners": int(row["HC"]) if pd.notna(row.get("HC")) else None,
                "fouls": int(row["HF"]) if pd.notna(row.get("HF")) else None,
                "yellow_cards": int(row["HY"]) if pd.notna(row.get("HY")) else None,
                "red_cards": int(row["HR"]) if pd.notna(row.get("HR")) else None,
            }

            away_stats = {
                "team_name": away_team,
                "is_home": False,
                "shots": int(row["AS"]) if pd.notna(row.get("AS")) else None,
                "shots_on_target": int(row["AST"]) if pd.notna(row.get("AST")) else None,
                "corners": int(row["AC"]) if pd.notna(row.get("AC")) else None,
                "fouls": int(row["AF"]) if pd.notna(row.get("AF")) else None,
                "yellow_cards": int(row["AY"]) if pd.notna(row.get("AY")) else None,
                "red_cards": int(row["AR"]) if pd.notna(row.get("AR")) else None,
            }

            # Betting Odds parsing
            odds_list: list[dict[str, Any]] = []

            # 1. Pinnacle Odds (1X2 & Over/Under 2.5)
            for prefix, bm_code in [("P", "PS"), ("B365", "B365"), ("Avg", "Avg"), ("Max", "Max")]:
                h_val = row.get(f"{prefix}H")
                d_val = row.get(f"{prefix}D")
                a_val = row.get(f"{prefix}A")
                if pd.notna(h_val) and pd.notna(d_val) and pd.notna(a_val):
                    try:
                        odds_list.extend([
                            {"bookmaker_code": bm_code, "market_type": "1x2", "selection": "home", "odds": float(h_val)},
                            {"bookmaker_code": bm_code, "market_type": "1x2", "selection": "draw", "odds": float(d_val)},
                            {"bookmaker_code": bm_code, "market_type": "1x2", "selection": "away", "odds": float(a_val)},
                        ])
                    except (ValueError, TypeError):
                        pass

                over_val = row.get(f"{prefix}>2.5")
                under_val = row.get(f"{prefix}<2.5")
                if pd.notna(over_val) and pd.notna(under_val):
                    try:
                        odds_list.extend([
                            {"bookmaker_code": bm_code, "market_type": "over_under_2.5", "selection": "over", "odds": float(over_val)},
                            {"bookmaker_code": bm_code, "market_type": "over_under_2.5", "selection": "under", "odds": float(under_val)},
                        ])
                    except (ValueError, TypeError):
                        pass

            match_record = {
                "league_code": league_code,
                "season_code": season,
                "home_team": home_team,
                "away_team": away_team,
                "kickoff": kickoff,
                "status": status,
                "ft_home_goals": fthg,
                "ft_away_goals": ftag,
                "ht_home_goals": hthg,
                "ht_away_goals": htag,
                "source": self.source_name,
                "stats": [home_stats, away_stats],
                "odds": odds_list,
            }

            # Run data validator
            validation_errors = data_validator.validate_match(match_record)
            if validation_errors:
                logger.debug("match_validation_warning", home=home_team, away=away_team, errors=validation_errors)

            match_record["quality_score"] = data_validator.calculate_quality_score(
                match_record, [home_stats, away_stats]
            )
            records.append(match_record)

        logger.info("fduk_parsed_matches", count=len(records), league=league_code, season=season)
        return records
