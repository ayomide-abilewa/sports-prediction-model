from __future__ import annotations

import asyncio
import json
import logging
import re
import socket
from datetime import datetime, timezone
from typing import Any
from rapidfuzz import fuzz

from backend.ingestion.team_mapper import TeamMapper

# Monkey-patch socket.getaddrinfo to prioritize AF_INET (IPv4) on Windows to avoid DNS 11004 errors
_orig_getaddrinfo = socket.getaddrinfo


def _patched_getaddrinfo(host: str, port: Any, family: int = 0, *args: Any, **kwargs: Any) -> Any:
    if family == 0 or family == socket.AF_UNSPEC or str(family) == "AddressFamily.AF_UNSPEC":
        family = socket.AF_INET
    return _orig_getaddrinfo(host, port, family, *args, **kwargs)


socket.getaddrinfo = _patched_getaddrinfo

import httpx

logger = logging.getLogger("sportybet_service")

SPORTY_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like"
        " Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.sportybet.com/ng/",
    "Origin": "https://www.sportybet.com",
    "Content-Type": "application/json",
}

# In-memory cache for event details and market maps
_SPORTY_CACHE: dict[str, Any] = {
    "upcoming_events": [],
    "upcoming_sync": 0,
    "live_events": [],
    "live_sync": 0,
    "event_details": {},  # eventId -> full market dictionary
}


def _get_httpx_client() -> httpx.Client:
    return httpx.Client(timeout=8.0, headers=SPORTY_HEADERS)


def fetch_sporty_upcoming_events() -> list[dict[str, Any]]:
    """Fetches upcoming football matches directly from SportyBet Nigeria."""
    now_ts = datetime.now().timestamp()
    if _SPORTY_CACHE["upcoming_events"] and (now_ts - _SPORTY_CACHE["upcoming_sync"]) < 120:
        return _SPORTY_CACHE["upcoming_events"]

    url = "https://www.sportybet.com/api/ng/factsCenter/wapUpcomingEvents?sportId=sr:sport:1"
    try:
        with _get_httpx_client() as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                events = data.get("data", [])
                if events:
                    _SPORTY_CACHE["upcoming_events"] = events
                    _SPORTY_CACHE["upcoming_sync"] = now_ts
                    return events
    except Exception as exc:
        logger.warning(f"Error fetching SportyBet upcoming events: {exc}")
    return _SPORTY_CACHE.get("upcoming_events", [])


def fetch_sporty_live_events() -> list[dict[str, Any]]:
    """Fetches currently live football matches from SportyBet."""
    now_ts = datetime.now().timestamp()
    if _SPORTY_CACHE["live_events"] and (now_ts - _SPORTY_CACHE["live_sync"]) < 60:
        return _SPORTY_CACHE["live_events"]

    url = "https://www.sportybet.com/api/ng/factsCenter/liveOrPrematchEvents?sportId=sr:sport:1"
    try:
        with _get_httpx_client() as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                groups = data.get("data", [])
                live_list = []
                for g in groups:
                    for ev in g.get("events", []):
                        if ev.get("matchStatus") in ["H1", "H2", "HT", "Live", "live"]:
                            live_list.append(ev)
                if live_list:
                    _SPORTY_CACHE["live_events"] = live_list
                    _SPORTY_CACHE["live_sync"] = now_ts
                    return live_list
    except Exception as exc:
        logger.warning(f"Error fetching SportyBet live events: {exc}")
    return _SPORTY_CACHE.get("live_events", [])


def sync_sporty_cache():
    """Refreshes SportyBet upcoming and live fixtures synchronously."""
    try:
        up = fetch_sporty_upcoming_events()
        lv = fetch_sporty_live_events()
        logger.info(f"SportyBet synchronized: {len(up)} upcoming, {len(lv)} live fixtures")
    except Exception as e:
        logger.warning(f"SportyBet sync error: {e}")


async def start_sporty_background_sync():
    """Initializes and runs a periodic background refresh for SportyBet live and upcoming data."""
    async def _loop():
        while True:
            try:
                await asyncio.to_thread(sync_sporty_cache)
            except Exception as e:
                logger.warning(f"SportyBet background sync failure: {e}")
            await asyncio.sleep(120)

    asyncio.create_task(_loop())


def fetch_sporty_event_detail(event_id: str) -> dict[str, Any]:
    """Fetches all 200-600+ deep markets (Corners, Cards, Handicaps, Player Props) for a SportyBet event."""
    if event_id in _SPORTY_CACHE["event_details"]:
        cached = _SPORTY_CACHE["event_details"][event_id]
        if (datetime.now().timestamp() - cached.get("_cached_at", 0)) < 300:
            return cached["data"]

    url = f"https://www.sportybet.com/api/ng/factsCenter/event?eventId={event_id}"
    try:
        with _get_httpx_client() as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                event_data = data.get("data", {})
                _SPORTY_CACHE["event_details"][event_id] = {
                    "data": event_data,
                    "_cached_at": datetime.now().timestamp(),
                }
                return event_data
    except Exception as exc:
        logger.warning(f"Error fetching SportyBet event details for {event_id}: {exc}")
    return {}


def parse_sporty_markets(event_data: dict[str, Any]) -> dict[str, Any]:
    """Parses raw SportyBet markets into organized, user-facing betting options with exact SportyBet IDs."""
    markets_list = event_data.get("markets", [])
    parsed: dict[str, list[dict[str, Any]]] = {
        "one_x_two": [],
        "double_chance": [],
        "goals_over_under": [],
        "both_teams_to_score": [],
        "handicap": [],
        "corners": [],
        "cards": [],
    }

    event_id = event_data.get("eventId")

    for m in markets_list:
        m_id = str(m.get("id"))
        desc = m.get("desc", "")
        group = m.get("group", "")
        specifier = m.get("specifier")
        outcomes = m.get("outcomes", [])

        # 1. 1X2 (Market 1)
        if m_id == "1":
            for oc in outcomes:
                parsed["one_x_two"].append({
                    "event_id": event_id,
                    "market_id": m_id,
                    "outcome_id": str(oc.get("id")),
                    "specifier": specifier,
                    "selection": oc.get("desc"),
                    "odds": float(oc.get("odds", 1.0)),
                    "market_name": "Full Time 1X2",
                })

        # 2. Double Chance (Market 10)
        elif m_id == "10":
            for oc in outcomes:
                parsed["double_chance"].append({
                    "event_id": event_id,
                    "market_id": m_id,
                    "outcome_id": str(oc.get("id")),
                    "specifier": specifier,
                    "selection": oc.get("desc"),
                    "odds": float(oc.get("odds", 1.0)),
                    "market_name": "Double Chance",
                })

        # 3. Over / Under (Market 18)
        elif m_id == "18":
            for oc in outcomes:
                total_val = specifier.replace("total=", "") if specifier and "total=" in specifier else ""
                parsed["goals_over_under"].append({
                    "event_id": event_id,
                    "market_id": m_id,
                    "outcome_id": str(oc.get("id")),
                    "specifier": specifier,
                    "selection": oc.get("desc"),
                    "total": total_val,
                    "odds": float(oc.get("odds", 1.0)),
                    "market_name": f"Over/Under {total_val} Goals",
                })

        # 4. GG / NG (Market 29)
        elif m_id == "29":
            for oc in outcomes:
                parsed["both_teams_to_score"].append({
                    "event_id": event_id,
                    "market_id": m_id,
                    "outcome_id": str(oc.get("id")),
                    "specifier": specifier,
                    "selection": oc.get("desc"),
                    "odds": float(oc.get("odds", 1.0)),
                    "market_name": "GG / NG (Both Teams To Score)",
                })

        # 5. Corners (Market 166: Over/Under, 162: 1X2, 165: Handicap)
        elif group == "Corners" or "corner" in desc.lower():
            for oc in outcomes:
                parsed["corners"].append({
                    "event_id": event_id,
                    "market_id": m_id,
                    "outcome_id": str(oc.get("id")),
                    "specifier": specifier,
                    "selection": oc.get("desc"),
                    "odds": float(oc.get("odds", 1.0)),
                    "market_name": f"Corners - {desc}",
                })

        # 6. Cards / Bookings (Market 139: O/U, 136: 1X2, 146: Red Card / Sending Off)
        elif group == "Bookings" or any(w in desc.lower() for w in ["booking", "card"]):
            for oc in outcomes:
                parsed["cards"].append({
                    "event_id": event_id,
                    "market_id": m_id,
                    "outcome_id": str(oc.get("id")),
                    "specifier": specifier,
                    "selection": oc.get("desc"),
                    "odds": float(oc.get("odds", 1.0)),
                    "market_name": f"Cards & Bookings - {desc}",
                })

        # 7. Handicaps (Market 14 & 16)
        elif m_id in ["14", "16"] or "handicap" in desc.lower():
            for oc in outcomes:
                parsed["handicap"].append({
                    "event_id": event_id,
                    "market_id": m_id,
                    "outcome_id": str(oc.get("id")),
                    "specifier": specifier,
                    "selection": oc.get("desc"),
                    "odds": float(oc.get("odds", 1.0)),
                    "market_name": f"Handicap ({desc})",
                })

    return parsed


def _normalize_sporty_team(name: str) -> str:
    normalized = TeamMapper.normalize_string(name)
    aliases = {
        "buyuksehir": "istanbul basaksehir",
        "istanbul buyuksehir": "istanbul basaksehir",
        "istanbul buyuksehir belediyespor": "istanbul basaksehir",
        "basaksehir": "istanbul basaksehir",
        "basaksehir fk": "istanbul basaksehir",
        "istanbul basaksehir fk": "istanbul basaksehir",
        "besiktas jk": "besiktas",
    }
    return aliases.get(normalized, normalized)


def _pick_sporty_option(
    parsed: dict[str, list[dict[str, Any]]], market: str, selection: str
) -> dict[str, Any] | None:
    market_key = TeamMapper.normalize_string(market)
    pick_key = TeamMapper.normalize_string(selection)
    side = "over" if "over" in pick_key or pick_key in {"yes", "gg"} else "under"

    if market_key in {"1x2", "match result"}:
        target = {"home": "home", "1": "home", "draw": "draw", "x": "draw", "away": "away", "2": "away"}.get(pick_key)
        options = parsed["one_x_two"]
        for option in options:
            option_key = TeamMapper.normalize_string(str(option.get("selection", "")))
            if option_key == target or (target == "home" and option_key in {"1", "home win"}) or (target == "away" and option_key in {"2", "away win"}):
                return option
        return None

    if market_key in {"double chance", "double_chance"}:
        target = {"1x": {"1x", "home or draw"}, "x2": {"x2", "draw or away"}, "12": {"12", "home or away"}}.get(pick_key)
        return next((o for o in parsed["double_chance"] if TeamMapper.normalize_string(str(o.get("selection", ""))) in (target or set())), None)

    if market_key.startswith("over under ") or market_key.startswith("over_under_"):
        total_match = re.search(r"(\d+(?:\.\d+)?)", market)
        total = total_match.group(1) if total_match else None
        for option in parsed["goals_over_under"]:
            option_total = str(option.get("total") or "")
            option_side = "over" if "over" in TeamMapper.normalize_string(str(option.get("selection", ""))) else "under"
            if total and option_total == total and side == option_side:
                return option
        return None

    if market_key in {"btts", "gg ng", "both teams to score"}:
        target = "yes" if pick_key in {"yes", "gg"} else "no"
        for option in parsed["both_teams_to_score"]:
            option_key = TeamMapper.normalize_string(str(option.get("selection", "")))
            if (target == "yes" and option_key in {"yes", "gg"}) or (target == "no" and option_key in {"no", "ng"}):
                return option
        return None

    if market_key in {"corners", "cards", "cards bookings"}:
        category = "corners" if market_key == "corners" else "cards"
        line_match = re.search(r"(\d+(?:\.\d+)?)", selection)
        target_line = line_match.group(1) if line_match else None
        for option in parsed[category]:
            option_text = str(option.get("selection", ""))
            option_key = TeamMapper.normalize_string(option_text)
            option_line_match = re.search(r"(\d+(?:\.\d+)?)", option_text)
            spec = str(option.get("specifier") or "")
            spec_line_match = re.search(r"total=(\d+(?:\.\d+)?)", spec)
            option_line = spec_line_match.group(1) if spec_line_match else (option_line_match.group(1) if option_line_match else None)
            option_side = "over" if "over" in option_key else "under" if "under" in option_key else ""
            if target_line and target_line == option_line and side == option_side:
                return option
        return None

    return None


def resolve_sportybet_booking_selections(legs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Resolve id-less local suggestions only when one matching live SportyBet fixture and market exists."""
    events = fetch_sporty_upcoming_events()
    resolved: list[dict[str, Any]] = []
    unresolved: list[str] = []

    for leg in legs:
        if leg.get("event_id") and leg.get("market_id") and leg.get("outcome_id"):
            resolved.append({
                "eventId": str(leg["event_id"]),
                "marketId": str(leg["market_id"]),
                "outcomeId": str(leg["outcome_id"]),
                "specifier": leg.get("specifier"),
            })
            continue

        fixture = str(leg.get("fixture", ""))
        pieces = re.split(r"\s+vs?\.?\s+", fixture, maxsplit=1, flags=re.IGNORECASE)
        if len(pieces) != 2:
            unresolved.append(fixture)
            continue

        wanted_home, wanted_away = (_normalize_sporty_team(part) for part in pieces)
        kickoff = leg.get("kickoff")
        wanted_time = None
        if kickoff:
            try:
                wanted_time = datetime.fromisoformat(str(kickoff).replace("Z", "+00:00"))
                if wanted_time.tzinfo is None:
                    wanted_time = wanted_time.replace(tzinfo=timezone.utc)
                wanted_time = wanted_time.timestamp()
            except ValueError:
                wanted_time = None

        event_matches: list[tuple[float, dict[str, Any]]] = []
        for event in events:
            home = _normalize_sporty_team(str(event.get("homeTeamName", "")))
            away = _normalize_sporty_team(str(event.get("awayTeamName", "")))
            home_score = fuzz.token_set_ratio(wanted_home, home)
            away_score = fuzz.token_set_ratio(wanted_away, away)
            if home_score < 82 or away_score < 82:
                continue
            start_ms = event.get("estimateStartTime")
            time_delta = abs((float(start_ms) / 1000) - wanted_time) if start_ms and wanted_time else None
            if time_delta is not None and time_delta > 36 * 60 * 60:
                continue
            score = min(home_score, away_score)
            if time_delta is not None:
                score -= time_delta / 3600 * 0.25
            event_matches.append((score, event))

        event_matches.sort(key=lambda item: item[0], reverse=True)
        if not event_matches or (len(event_matches) > 1 and event_matches[0][0] - event_matches[1][0] < 3):
            unresolved.append(fixture)
            continue

        event = event_matches[0][1]
        event_id = str(event.get("eventId", ""))
        detail = fetch_sporty_event_detail(event_id)
        parsed = parse_sporty_markets(detail or event)
        option = _pick_sporty_option(parsed, str(leg.get("market", "")), str(leg.get("selection", "")))
        if not option or not option.get("market_id") or not option.get("outcome_id"):
            unresolved.append(fixture)
            continue

        leg["event_id"] = str(option.get("event_id") or event_id)
        leg["market_id"] = str(option["market_id"])
        leg["outcome_id"] = str(option["outcome_id"])
        leg["specifier"] = option.get("specifier")
        if option.get("odds"):
            leg["odds"] = float(option["odds"])
        resolved.append({
            "eventId": leg["event_id"],
            "marketId": leg["market_id"],
            "outcomeId": leg["outcome_id"],
            "specifier": leg["specifier"],
        })

    return resolved, unresolved


def generate_real_sportybet_booking_code(selections: list[dict[str, Any]]) -> dict[str, Any]:
    """Submits selections directly to SportyBet Nigeria official booking API.
    Returns the genuine 6-character booking code (e.g. 'NZM9X0') and official shareURL.
    """
    if not selections:
        return {"success": False, "error": "No selections provided"}

    clean_selections = []
    for s in selections:
        ev_id = s.get("eventId") or s.get("event_id")
        m_id = s.get("marketId") or s.get("market_id")
        oc_id = s.get("outcomeId") or s.get("outcome_id")
        spec = s.get("specifier")

        if ev_id and m_id and oc_id:
            clean_selections.append({
                "eventId": str(ev_id),
                "marketId": str(m_id),
                "outcomeId": str(oc_id),
                "specifier": spec if spec else None,
            })

    if len(clean_selections) != len(selections):
        return {"success": False, "error": "Every selection must include event, market, and outcome IDs."}

    url = "https://www.sportybet.com/api/ng/orders/share"
    payload = {"selections": clean_selections}

    try:
        with _get_httpx_client() as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("bizCode") == 10000:
                    share_data = data.get("data", {})
                    share_code = share_data.get("shareCode")
                    if not share_code:
                        return {"success": False, "message": "SportyBet accepted the request but returned no share code."}
                    return {
                        "success": True,
                        "share_code": share_code,
                        "share_url": share_data.get("shareURL"),
                        "deadline": share_data.get("deadline"),
                        "leg_count": len(clean_selections),
                    }
                else:
                    return {
                        "success": False,
                        "message": data.get("message", "SportyBet rejected selection payload"),
                        "biz_code": data.get("bizCode"),
                    }
            return {"success": False, "message": f"SportyBet returned HTTP {resp.status_code}."}
    except Exception as exc:
        logger.error(f"Error booking SportyBet ticket: {exc}")
        return {"success": False, "error": str(exc)}

    return {"success": False, "message": "Failed to connect to SportyBet order service"}
