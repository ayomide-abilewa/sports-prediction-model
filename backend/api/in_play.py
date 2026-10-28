from __future__ import annotations

import random
import re
import zlib
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.engine import get_db
from backend.models.league import Season
from backend.models.match import Match, MatchStatistics
from backend.probability.in_play import in_play_engine
from backend.api.predictions import _get_fitted_model
from backend.ingestion.team_mapper import team_mapper
from backend.ingestion.sportybet_service import (
    fetch_sporty_live_events,
    fetch_sporty_event_detail,
    parse_sporty_markets,
)

router = APIRouter(prefix="/in-play", tags=["In-Play & Live Analytics"])


def _live_minute(event: dict[str, Any]) -> int | None:
    for key in (
        "liveMinute", "live_minute", "minute", "playedMinute", "played_minute",
        "elapsedMinute", "elapsed_minute", "matchMinute", "match_minute",
        "currentMinute", "current_minute", "liveTime", "live_time", "playedTime", "played_time",
    ):
        value = event.get(key)
        if isinstance(value, dict):
            value = value.get("minute")
        match = re.search(r"\d{1,3}", str(value or ""))
        if match:
            minute = int(match.group())
            if 0 <= minute <= 130:
                return minute
    return None


def _live_stat(event: dict[str, Any], *keys: str) -> float | None:
    sources = [event]
    stats = event.get("stats")
    if isinstance(stats, dict):
        sources.append(stats)
    for source in sources:
        for key in keys:
            value = source.get(key)
            try:
                if value is not None:
                    return float(str(value).replace("%", ""))
            except (TypeError, ValueError):
                continue
    return None


def _prematch_goals(model: Any, home: str, away: str) -> tuple[float, float] | None:
    if model is None:
        return None
    canonical_home, _ = team_mapper.resolve(home)
    canonical_away, _ = team_mapper.resolve(away)
    if canonical_home not in model.team_idx or canonical_away not in model.team_idx:
        return None
    try:
        expected = model.predict_match(canonical_home, canonical_away).get("expected_goals", {})
        xg_home, xg_away = expected.get("home"), expected.get("away")
        if xg_home is not None and xg_away is not None:
            return float(xg_home), float(xg_away)
    except Exception:
        return None
    return None


@router.get("")
async def list_live_matches(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Returns all active live matches with real-time in-play probabilities and AI recommendations."""
    dc = await _get_fitted_model(db)
    # 1. First, check for database in-play fixtures
    stmt = (
        select(Match)
        .options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.season).selectinload(Season.league),
            selectinload(Match.statistics),
        )
        .where(Match.status == "in_play")
        .order_by(Match.kickoff.asc())
    )
    res = await db.execute(stmt)
    db_live_matches = res.scalars().all()

    results: list[dict[str, Any]] = []

    # Process database live matches if any
    for m in db_live_matches:
        score_h = m.ft_home_goals if m.ft_home_goals is not None else 0
        score_a = m.ft_away_goals if m.ft_away_goals is not None else 0

        home_stats = next((s for s in m.statistics if s.is_home), None)
        away_stats = next((s for s in m.statistics if not s.is_home), None)

        possession_h = home_stats.possession if home_stats else None
        sot_h = home_stats.shots_on_target if home_stats else None
        sot_a = away_stats.shots_on_target if away_stats else None
        corners_h = home_stats.corners if home_stats else None
        corners_a = away_stats.corners if away_stats else None
        cards_h = home_stats.yellow_cards if home_stats else None
        cards_a = away_stats.yellow_cards if away_stats else None
        red_cards_h = home_stats.red_cards if home_stats else 0
        red_cards_a = away_stats.red_cards if away_stats else 0

        minute = getattr(m, "live_minute", None)

        live_stats_payload = {
            "possession_home": possession_h,
            "shots_on_target_home": sot_h,
            "shots_on_target_away": sot_a,
            "corners_home": corners_h,
            "corners_away": corners_a,
            "cards_home": cards_h,
            "cards_away": cards_a,
            "red_cards_home": red_cards_h,
            "red_cards_away": red_cards_a,
        }

        baseline = _prematch_goals(dc, m.home_team.name, m.away_team.name)
        in_play_res = in_play_engine.calculate_in_play_probabilities(
            home_team=m.home_team.name,
            away_team=m.away_team.name,
            minute=minute or 1,
            score_home=score_h,
            score_away=score_a,
            pre_match_xg_home=baseline[0],
            pre_match_xg_away=baseline[1],
            live_stats=live_stats_payload,
        ) if minute is not None and baseline is not None else None

        results.append({
            "match_id": m.id,
            "fixture": f"{m.home_team.name} vs {m.away_team.name}",
            "home_team": m.home_team.name,
            "away_team": m.away_team.name,
            "league": m.season.league.name if m.season and m.season.league else "Live League",
            "kickoff": m.kickoff.isoformat(),
            "status": "in_play",
            "live_minute": minute,
            "period": "Live clock unavailable" if minute is None else ("1st Half" if minute <= 45 else ("Half Time" if minute == 45 else "2nd Half")),
            "score": {"home": score_h, "away": score_a},
            "live_stats": live_stats_payload,
            "surest_in_play_pick": in_play_res["surest_in_play_pick"] if in_play_res else None,
            "top_in_play_picks": in_play_res["top_in_play_picks"] if in_play_res else [],
            "live_narrative": in_play_res["live_narrative"] if in_play_res else "Live forecast paused: a reliable clock and team-specific pre-match model are both required.",
            "remaining_projected_xg": in_play_res["remaining_projected_xg"] if in_play_res else None,
            "next_goal_probabilities": in_play_res["next_goal"] if in_play_res else None,
            "all_live_markets": in_play_res["all_live_markets"] if in_play_res else [],
        })

    # 2. Fetch live real matches from SportyBet
    try:
        sporty_live = fetch_sporty_live_events()
        for ev in sporty_live[:8]:
            home = ev.get("homeTeamName")
            away = ev.get("awayTeamName")
            eid = ev.get("eventId")
            if not home or not away or not eid:
                continue

            # Parse score from setScore "0:0", "1:2"
            set_score = str(ev.get("setScore", "0:0"))
            try:
                parts = set_score.split(":")
                score_h = int(parts[0].strip())
                score_a = int(parts[1].strip())
            except Exception:
                score_h, score_a = 0, 0

            status_code = ev.get("matchStatus", "H1")
            minute = _live_minute(ev)
            period_str = {"H1": "1st Half", "HT": "Half Time", "H2": "2nd Half"}.get(status_code, "Live")

            cat_name = ev.get("sport", {}).get("category", {}).get("name", "Football")
            tourn_name = ev.get("sport", {}).get("category", {}).get("tournament", {}).get("name", "")
            league_str = f"{cat_name} - {tourn_name}" if tourn_name else cat_name

            # Generate realistic live in-game metrics based on current live state
            live_stats_payload = {
                "possession_home": _live_stat(ev, "possessionHome", "homePossession", "possession_home"),
                "shots_on_target_home": _live_stat(ev, "shotsOnTargetHome", "homeShotsOnTarget", "shots_on_target_home"),
                "shots_on_target_away": _live_stat(ev, "shotsOnTargetAway", "awayShotsOnTarget", "shots_on_target_away"),
                "corners_home": _live_stat(ev, "cornersHome", "homeCorners", "corners_home"),
                "corners_away": _live_stat(ev, "cornersAway", "awayCorners", "corners_away"),
                "cards_home": _live_stat(ev, "cardsHome", "homeCards", "cards_home"),
                "cards_away": _live_stat(ev, "cardsAway", "awayCards", "cards_away"),
                "red_cards_home": _live_stat(ev, "redCardsHome", "homeRedCards", "red_cards_home") or 0,
                "red_cards_away": _live_stat(ev, "redCardsAway", "awayRedCards", "red_cards_away") or 0,
            }

            baseline = _prematch_goals(dc, home, away)
            in_play_res = in_play_engine.calculate_in_play_probabilities(
                home_team=home, away_team=away, minute=minute or 1,
                score_home=score_h, score_away=score_a,
                pre_match_xg_home=baseline[0], pre_match_xg_away=baseline[1],
                live_stats=live_stats_payload,
            ) if minute is not None and baseline is not None else None

            numeric_id = abs(zlib.crc32(eid.encode("utf-8"))) % 1000000 + 100000

            results.append({
                "match_id": numeric_id,
                "fixture": f"{home} vs {away}",
                "home_team": home,
                "away_team": away,
                "league": league_str,
                "kickoff": datetime.fromtimestamp(int(ev.get("estimateStartTime") or 0) / 1000, timezone.utc).isoformat() if ev.get("estimateStartTime") else None,
                "status": "in_play",
                "live_minute": minute,
                "period": period_str if minute is not None else "Live clock unavailable",
                "score": {"home": score_h, "away": score_a},
                "live_stats": live_stats_payload,
                "surest_in_play_pick": in_play_res["surest_in_play_pick"] if in_play_res else None,
                "top_in_play_picks": in_play_res["top_in_play_picks"] if in_play_res else [],
                "live_narrative": in_play_res["live_narrative"] if in_play_res else "Live forecast paused: a reliable clock and team-specific pre-match model are both required.",
                "remaining_projected_xg": in_play_res["remaining_projected_xg"] if in_play_res else None,
                "next_goal_probabilities": in_play_res["next_goal"] if in_play_res else None,
                "all_live_markets": in_play_res["all_live_markets"] if in_play_res else [],
            })
    except Exception:
        pass

    return results


@router.get("/{match_id}")
async def get_match_in_play_details(
    match_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Returns deep in-play modeling and all live market options for a single match."""
    stmt = (
        select(Match)
        .options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.season).selectinload(Season.league),
            selectinload(Match.statistics),
        )
        .where(Match.id == match_id)
    )
    res = await db.execute(stmt)
    m = res.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Match not found")

    score_h = m.ft_home_goals if m.ft_home_goals is not None else 0
    score_a = m.ft_away_goals if m.ft_away_goals is not None else 0
    minute = getattr(m, "live_minute", None)

    home_stats = next((s for s in m.statistics if s.is_home), None)
    away_stats = next((s for s in m.statistics if not s.is_home), None)

    live_stats = {
        "possession_home": home_stats.possession if home_stats else None,
        "shots_on_target_home": home_stats.shots_on_target if home_stats else None,
        "shots_on_target_away": away_stats.shots_on_target if away_stats else None,
        "corners_home": home_stats.corners if home_stats else None,
        "corners_away": away_stats.corners if away_stats else None,
        "cards_home": home_stats.yellow_cards if home_stats else None,
        "cards_away": away_stats.yellow_cards if away_stats else None,
        "red_cards_home": home_stats.red_cards if home_stats else 0,
        "red_cards_away": away_stats.red_cards if away_stats else 0,
    }

    baseline = _prematch_goals(await _get_fitted_model(db), m.home_team.name, m.away_team.name)
    in_play_res = in_play_engine.calculate_in_play_probabilities(
        home_team=m.home_team.name,
        away_team=m.away_team.name,
        minute=minute or 1,
        score_home=score_h,
        score_away=score_a,
        pre_match_xg_home=baseline[0],
        pre_match_xg_away=baseline[1],
        live_stats=live_stats,
    ) if minute is not None and baseline is not None else None

    return {
        "match_id": m.id,
        "fixture": f"{m.home_team.name} vs {m.away_team.name}",
        "home_team": m.home_team.name,
        "away_team": m.away_team.name,
        "league": m.season.league.name if m.season and m.season.league else "",
        "status": m.status,
        "live_minute": minute,
        "score": {"home": score_h, "away": score_a},
        "in_play_model": in_play_res if in_play_res is not None else {
            "surest_in_play_pick": None,
            "top_in_play_picks": [],
            "live_narrative": "Live forecast paused: a reliable clock and team-specific pre-match model are both required.",
            "remaining_projected_xg": None,
            "next_goal": None,
            "all_live_markets": [],
        },
    }
