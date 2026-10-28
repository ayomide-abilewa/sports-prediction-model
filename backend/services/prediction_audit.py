from __future__ import annotations

import asyncio
import re
import unicodedata
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.match import Match
from backend.models.league import Season
from backend.models.prediction import Prediction
from backend.ingestion.sportscore_results import fetch_finished_results


def _grade(prediction: Prediction, match: Match) -> str | None:
    if match.ft_home_goals is None or match.ft_away_goals is None:
        return None

    home_goals, away_goals = match.ft_home_goals, match.ft_away_goals
    result = "home" if home_goals > away_goals else "away" if away_goals > home_goals else "draw"
    selection = prediction.selection.casefold()
    market = prediction.market_type.casefold()

    if market == "1x2":
        if selection in {"draw", "x"}:
            won = result == "draw"
        elif selection == "1":
            won = result == "home"
        elif selection == "2":
            won = result == "away"
        elif "home" in selection or selection.startswith(match.home_team.name.casefold()):
            won = result == "home"
        elif "away" in selection or selection.startswith(match.away_team.name.casefold()):
            won = result == "away"
        else:
            return None
    elif market in {"match goals", "goals"}:
        line_match = re.search(r"(over|under)\s+(\d+(?:\.\d+)?)", selection)
        if not line_match:
            return None
        line = float(line_match.group(2))
        total = home_goals + away_goals
        won = total > line if line_match.group(1) == "over" else total < line
    elif market in {"gg / ng", "btts"}:
        both_scored = home_goals > 0 and away_goals > 0
        wants_yes = "yes" in selection or "gg" in selection
        won = both_scored == wants_yes
    elif market == "double chance":
        if "1x" in selection or ("home" in selection and "draw" in selection):
            won = result in {"home", "draw"}
        elif "x2" in selection or ("draw" in selection and "away" in selection):
            won = result in {"away", "draw"}
        elif "12" in selection or ("home" in selection and "away" in selection):
            won = result in {"home", "away"}
        else:
            return None
    elif market == "handicap":
        specifier = (prediction.model_output or {}).get("specifier") or ""
        line_match = re.search(r"(?:hcp|handicap|home|away)=?([+-]?\d+(?:\.\d+)?)", str(specifier), re.I)
        if not line_match:
            line_match = re.search(r"([+-]\d+(?:\.\d+)?)", selection)
        if not line_match:
            return None
        line = float(line_match.group(1))
        adjusted_home = home_goals + line
        if "away" in selection or selection.startswith(match.away_team.name.casefold()):
            adjusted_home = home_goals - line
        elif not ("home" in selection or selection.startswith(match.home_team.name.casefold())):
            return None
        won = adjusted_home > away_goals
        if adjusted_home == away_goals:
            return "push"
    else:
        return None

    if prediction.market_type.casefold() in {"match goals", "goals"} and home_goals + away_goals == line:
        return "push"
    return "won" if won else "lost"


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
    normalized = normalized.replace("k ln", "koln")
    return re.sub(r"\bcologne\b", "koln", normalized)


def _team_name_score(left: str, right: str) -> float:
    left = _normalize_name(left)
    right = _normalize_name(right)
    if left == right:
        return 100.0
    token_score = fuzz.token_set_ratio(left, right)
    left_tokens, right_tokens = set(left.split()), set(right.split())
    generic = {"fc", "cf", "sc", "afc", "vfl", "sv", "fsv", "sg", "sk", "fk", "cd", "ce", "1", "05", "98", "1848"}
    if token_score >= 90 and (left_tokens - right_tokens <= generic or right_tokens - left_tokens <= generic):
        return token_score
    # Reject short-name containment such as Newcastle vs Newcastle Jets.
    return min(fuzz.ratio(left, right), token_score)


def _reconcile_result(match: Match, results: list[dict[str, Any]]) -> bool:
    """Apply a result only when both team names identify one unambiguous event."""
    home = _normalize_name(match.home_team.name)
    away = _normalize_name(match.away_team.name)
    best: tuple[int, dict[str, Any]] | None = None
    ambiguous = False
    for result in results:
        if str(result.get("status", "")).casefold() not in {"finished", "ft", "full time"}:
            continue
        home_score = _team_name_score(home, str(result.get("home") or ""))
        away_score = _team_name_score(away, str(result.get("away") or ""))
        # Keep team order fixed; a reversed fixture must never be treated as a match.
        score = min(home_score, away_score)
        if score < 80:
            continue
        if best is None or score > best[0]:
            best = (score, result)
            ambiguous = False
        elif score == best[0]:
            # Ambiguous same-name reserve/youth fixtures are left unsettled.
            ambiguous = True
    if best is None or ambiguous:
        return False
    try:
        home_goals = int(best[1]["home_score"])
        away_goals = int(best[1]["away_score"])
    except (KeyError, TypeError, ValueError):
        return False
    match.ft_home_goals = home_goals
    match.ft_away_goals = away_goals
    match.status = "finished"
    return True


def _sportscore_competition_slug(match: Match) -> str | None:
    league = (match.season.league.name if match.season and match.season.league else "").casefold()
    known = {
        "afc champions league elite": "afc-champions-league-elite",
        "copa del rey": "copa-del-rey",
        "dfb pokal": "dfb-pokal",
        "scottish cup": "scottish-cup",
        "serie a": "italian-serie-a",
        "serie b": "italian-serie-b",
        "turkiye kupasi": "turkish-cup",
        "ukraine cup": "ukrainian-cup",
        "league cup": "portuguese-league-cup",
    }
    return known.get(league)


async def build_prediction_audit(db: AsyncSession, date_str: str | None = None) -> dict[str, Any]:
    """Settle carried picks; recover one legacy surest pick per old fixture."""
    stmt = (
        select(Prediction)
        .join(Prediction.match)
        .options(
            selectinload(Prediction.match).selectinload(Match.home_team),
            selectinload(Prediction.match).selectinload(Match.away_team),
            selectinload(Prediction.match).selectinload(Match.season),
            selectinload(Prediction.match).selectinload(Match.season).selectinload(Season.league),
        )
        .where(Match.source.like("sportybet:%"))
        .order_by(Match.kickoff.desc())
    )
    if date_str:
        try:
            audit_day = date.fromisoformat(date_str)
        except ValueError:
            audit_day = datetime.now(ZoneInfo("Africa/Lagos")).date()
        local_zone = ZoneInfo("Africa/Lagos")
        start = datetime.combine(audit_day, time.min, tzinfo=local_zone).astimezone(timezone.utc).replace(tzinfo=None)
        end = datetime.combine(audit_day + timedelta(days=1), time.min, tzinfo=local_zone).astimezone(timezone.utc).replace(tzinfo=None)
        stmt = stmt.where(Match.kickoff >= start, Match.kickoff < end)

    rows = (await db.execute(stmt)).scalars().all()
    if date_str and rows and any(p.match.status != "finished" for p in rows):
        try:
            audit_day = date.fromisoformat(date_str)
            result_days = (audit_day - timedelta(days=1), audit_day)
            daily_results = await asyncio.gather(*(fetch_finished_results(day) for day in result_days))
            results = [event for batch in daily_results for event in batch]
            reconciled: set[int] = set()
            for prediction in rows:
                match = prediction.match
                if match.id in reconciled or match.status == "finished":
                    continue
                if _reconcile_result(match, results):
                    reconciled.add(match.id)
            unresolved = {
                (slug, day)
                for prediction in rows
                if prediction.match.status != "finished"
                for slug in [_sportscore_competition_slug(prediction.match)]
                if slug
                for day in result_days
            }
            if unresolved:
                competition_results = await asyncio.gather(*(
                    fetch_finished_results(day, slug) for slug, day in unresolved
                ))
                unique: dict[tuple[str, str, str, str], dict[str, Any]] = {}
                for event in results + [event for batch in competition_results for event in batch]:
                    key = (
                        str(event.get("home", "")).casefold(),
                        str(event.get("away", "")).casefold(),
                        str(event.get("time", "")),
                        str(event.get("home_score", "")) + "-" + str(event.get("away_score", "")),
                    )
                    unique[key] = event
                results = list(unique.values())
                for prediction in rows:
                    match = prediction.match
                    if match.id in reconciled or match.status == "finished":
                        continue
                    if _reconcile_result(match, results):
                        reconciled.add(match.id)
        except (ValueError, OverflowError):
            pass
    predictions_by_match: dict[int, list[Prediction]] = {}
    for prediction in rows:
        predictions_by_match.setdefault(prediction.match_id, []).append(prediction)

    today = datetime.now(ZoneInfo("Africa/Lagos")).date()
    fixtures_by_match: dict[int, list[Prediction]] = {}
    legacy_reconstructed: set[int] = set()
    for match_id, predictions in predictions_by_match.items():
        match = predictions[0].match
        carried = [p for p in predictions if (p.model_output or {}).get("carried")]
        if carried:
            chosen = max(carried, key=lambda p: p.generated_at)
        else:
            # Before carried selections were tagged, the platform stored all
            # markets for a fixture. Recreate the old surest-pick rule for
            # completed days so those saved picks can still be audited.
            if match.kickoff.replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Africa/Lagos")).date() >= today:
                continue
            high_conviction = [
                p for p in predictions
                if p.probability >= 0.65 and (p.available_odds or 0) >= 1.12
            ]
            pool = high_conviction or predictions
            chosen = max(pool, key=lambda p: (p.probability, p.expected_value or -1.0))
            legacy_reconstructed.add(match_id)

        outcome = _grade(chosen, match) if match.status == "finished" else None
        if match.status == "finished" and outcome is None:
            chosen.outcome = "ungraded"
        elif outcome:
            chosen.outcome = outcome
            chosen.settled = True
        fixtures_by_match[match_id] = [chosen]

    fixtures: list[dict[str, Any]] = []
    for predictions in fixtures_by_match.values():
        match = predictions[0].match
        graded = sorted(predictions, key=lambda prediction: prediction.probability, reverse=True)
        main = next((p for p in graded if p.market_type == "1X2"), graded[0])
        prop = next((p for p in graded if p.id != main.id and p.market_type != "1X2"), None)

        def format_pick(p: Prediction | None) -> dict[str, Any] | None:
            if p is None:
                return None
            status = p.outcome if p.settled else ("ungraded" if p.outcome == "ungraded" else "pending")
            odds = p.available_odds
            return {
                "name": p.selection,
                "market": p.market_type,
                "probability": p.calibrated_prob or p.probability,
                "odds": odds,
                "status": status,
                "status_symbol": "✅" if status == "won" else "❌" if status == "lost" else "⌛" if status == "pending" else "?",
                "profit": (
                    round(odds - 1.0, 2) if status == "won" and odds and odds > 1
                    else (-1.0 if status == "lost" else 0.0) if odds and odds > 1
                    else None
                ),
            }

        fixtures.append({
            "fixture": f"{match.home_team.name} vs {match.away_team.name}",
            "home_team": match.home_team.name,
            "away_team": match.away_team.name,
            "league": match.season.league.name if match.season and match.season.league else "",
            "matchday": match.season.season_code if match.season else "",
            "played_date": match.kickoff.replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Africa/Lagos")).date().isoformat(),
            "kickoff_time": match.kickoff.strftime("%H:%M UTC"),
            "ft_score": (
                f"{match.ft_home_goals}-{match.ft_away_goals}"
                if match.status == "finished" and match.ft_home_goals is not None and match.ft_away_goals is not None
                else "Result unavailable"
                if match.kickoff.replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Africa/Lagos")).date() < today
                else "Pending result"
            ),
            "main_pick": format_pick(main),
            "best_prop": format_pick(prop),
            "pick_tracking": "reconstructed from saved forecasts" if match.id in legacy_reconstructed else "exact carried selection",
        })

    main_picks = [fixture["main_pick"] for fixture in fixtures if fixture["main_pick"]]
    settled = [pick for pick in main_picks if pick["status"] in {"won", "lost", "push"}]
    wins = sum(pick["status"] == "won" for pick in settled)
    losses = sum(pick["status"] == "lost" for pick in settled)
    picks_with_odds = [pick for pick in settled if pick["profit"] is not None]
    net_profit = round(sum(pick["profit"] for pick in picks_with_odds), 2)
    props = [fixture["best_prop"] for fixture in fixtures if fixture["best_prop"]]
    props_settled = [pick for pick in props if pick["status"] in {"won", "lost", "push"}]
    prop_wins = sum(pick["status"] == "won" for pick in props_settled)
    prop_losses = sum(pick["status"] == "lost" for pick in props_settled)

    return {
        "audit_date": date_str or "all",
        "title": "Tracked prediction results",
        "subtitle": "Each fixture is checked against final scores. Older picks are reconstructed from saved forecasts because the exact slip selection was not recorded at the time.",
        "summary": {
            "main_picks": {
                "graded": len(settled), "wins": wins, "losses": losses,
                "win_rate": round(wins / len(settled) * 100, 1) if settled else 0.0,
                "net_profit": net_profit,
                "roi": round(net_profit / len(picks_with_odds) * 100, 1) if picks_with_odds else 0.0,
            },
            "best_props": {
                "graded": len(props_settled), "wins": prop_wins, "losses": prop_losses,
                "pushes": sum(pick["status"] == "push" for pick in props_settled),
                "win_rate": round(prop_wins / len(props_settled) * 100, 1) if props_settled else 0.0,
            },
            "brier_calibration": None,
        },
        "formatted_text": (
            f"Tracked predictions graded: {len(settled)}. Wins: {wins}; losses: {losses}; "
            f"net return: {net_profit:+.2f} units."
            if settled else f"{len(fixtures)} carried picks are being tracked. No verified final scores are available to grade yet."
        ),
        "fixtures": fixtures,
    }
