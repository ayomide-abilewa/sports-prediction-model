from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from backend.api.predictions import _build_sporty_match_item, _get_fitted_model
from backend.db.engine import AsyncSessionLocal
from backend.ingestion.sportybet_service import (
    fetch_sporty_event_detail,
    fetch_sporty_upcoming_events,
    generate_real_sportybet_booking_code,
)
from backend.services.audit_service import build_audit_report

# In-memory cache for today's match items to ensure sub-second response times
_TODAY_CACHE: dict[str, Any] = {
    "timestamp": 0.0,
    "date": None,
    "items": [],
}


async def get_today_matches(force_refresh: bool = False) -> list[dict[str, Any]]:
    """Returns today's active matches with Surest Prediction and Best Prop."""
    now_utc = datetime.now(timezone.utc)
    target_date = datetime.now(ZoneInfo("Africa/Lagos")).date()

    # Use 5-minute cache to avoid hammering SportyBet on repeated button clicks
    if (
        not force_refresh
        and _TODAY_CACHE["date"] == target_date
        and time.time() - _TODAY_CACHE["timestamp"] < 300
        and _TODAY_CACHE["items"]
    ):
        return _TODAY_CACHE["items"]

    async with AsyncSessionLocal() as session:
        dc = await _get_fitted_model(session)

    events = await asyncio.to_thread(fetch_sporty_upcoming_events)
    today_items: list[dict[str, Any]] = []

    for ev in events:
        st = ev.get("estimateStartTime")
        if not st:
            continue
        try:
            dt = datetime.fromtimestamp(st / 1000, tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            continue

        if dt > now_utc and dt.astimezone(ZoneInfo("Africa/Lagos")).date() == target_date:
            item = _build_sporty_match_item(ev, dc)
            if item and item.get("surest_prediction"):
                today_items.append(item)

    # Sort today's items by kickoff time
    today_items.sort(key=lambda x: x.get("kickoff", ""))

    _TODAY_CACHE["timestamp"] = time.time()
    _TODAY_CACHE["date"] = target_date
    _TODAY_CACHE["items"] = today_items
    return today_items


def format_today_fixtures_text(matches: list[dict[str, Any]]) -> str:
    """Formats today's upcoming fixtures for the user."""
    if not matches:
        return "📅 *No upcoming scheduled fixtures remaining for today.*"

    today_str = datetime.now(ZoneInfo("Africa/Lagos")).strftime("%A, %d %B %Y")
    lines = [f"📅 *Today's Football Fixtures ({today_str})*\n"]
    lines.append(f"_Showing top upcoming matches with verified odds from live feed:_\n")

    for i, m in enumerate(matches[:12], 1):
        try:
            kick_dt = datetime.fromisoformat(m["kickoff"].replace("Z", "+00:00")).astimezone(
                ZoneInfo("Africa/Lagos")
            )
            time_display = kick_dt.strftime("%H:%M WAT")
        except Exception:
            time_display = "TBD"

        league = m.get("league", "Football")
        lines.append(f"{i}. *{m['fixture']}*\n   🏆 `{league}` | 🕒 `{time_display}`")

    lines.append("\n💡 *Tap '🎯 Daily Predictions' to see the Surest Pick and Best Prop for each match!*")
    return "\n".join(lines)


def format_today_predictions_text(matches: list[dict[str, Any]]) -> str:
    """Formats 1 Surest Pick and 1 Best Prop per match for today."""
    if not matches:
        return "🎯 *No match predictions available for today's schedule yet.*"

    today_str = datetime.now(ZoneInfo("Africa/Lagos")).strftime("%A, %d %b")
    lines = [
        f"🎯 *MATCH PREDICTIONS — {today_str}*\n"
        f"_Every fixture features strictly 1 Definitive Surest Pick + 1 Best Prop:_\n"
    ]

    for i, m in enumerate(matches[:8], 1):
        try:
            kick_dt = datetime.fromisoformat(m["kickoff"].replace("Z", "+00:00")).astimezone(
                ZoneInfo("Africa/Lagos")
            )
            time_display = kick_dt.strftime("%H:%M WAT")
        except Exception:
            time_display = "TBD"

        sp = m.get("surest_prediction") or {}
        bp = m.get("best_prop") or {}

        sp_text = (
            f"   🎯 *Surest:* `{sp.get('market')}: {sp.get('selection')}` @ *{sp.get('odds', 1.0):.2f}* "
            f"({sp.get('prob', 0.0) * 100:.0f}%)"
            if sp
            else "   🎯 *Surest:* Pending"
        )
        bp_text = (
            f"   🔥 *Prop:* `{bp.get('market')}: {bp.get('selection')}` @ *{bp.get('odds', 1.0):.2f}* "
            f"({bp.get('prob', 0.0) * 100:.0f}%)"
            if bp
            else "   🔥 *Prop:* Neutral line"
        )

        lines.append(f"{i}. *{m['fixture']}* (🕒 `{time_display}`)\n{sp_text}\n{bp_text}\n")

    lines.append("🎫 *To get an official SportyBet ticket, tap a slip option below (2x, 5x, 15x, 100x)!*")
    return "\n".join(lines)


def format_bankers_text(matches: list[dict[str, Any]]) -> str:
    """Filters highest-probability banker selections for today."""
    bankers = []
    for m in matches:
        sp = m.get("surest_prediction")
        if sp and sp.get("prob", 0) >= 0.70 and sp.get("odds", 0) >= 1.05:
            bankers.append((m, sp))

    bankers.sort(key=lambda item: (item[1]["prob"], item[1]["odds"]), reverse=True)

    if not bankers:
        return "🔒 *No Tier-1 Banker selections (≥70% probability) found for remaining games today.*"

    today_str = datetime.now(ZoneInfo("Africa/Lagos")).strftime("%A, %d %b")
    lines = [f"🔒 *TIER 1 BANKERS — {today_str}*\n_High probability mathematically validated picks:_\n"]

    for i, (m, sp) in enumerate(bankers[:6], 1):
        try:
            kick_dt = datetime.fromisoformat(m["kickoff"].replace("Z", "+00:00")).astimezone(
                ZoneInfo("Africa/Lagos")
            )
            time_display = kick_dt.strftime("%H:%M WAT")
        except Exception:
            time_display = "TBD"

        lines.append(
            f"{i}. *{m['fixture']}* (🕒 `{time_display}`)\n"
            f"   👉 `{sp['market']}: {sp['selection']}` @ *{sp['odds']:.2f}*\n"
            f"   📊 Model Probability: *{sp['prob'] * 100:.1f}%* | Tier: `Banker`\n"
        )

    lines.append("🎫 *Tap '2x Banker Slip' to generate a verified booking code with these selections!*")
    return "\n".join(lines)


async def build_custom_slip_response(
    matches: list[dict[str, Any]],
    slip_name: str,
    target_odds: float,
    strategy: str = "balanced",  # "banker", "balanced", "sharp", "mega", "risky"
) -> str:
    """Builds a curated slip reaching target_odds and books it directly on SportyBet."""
    if not matches:
        return f"⚠️ *No live matches available today to build {slip_name}.*"

    # Pool candidate legs
    candidates: list[dict[str, Any]] = []

    for m in matches:
        sp = m.get("surest_prediction")
        bp = m.get("best_prop")

        if sp and sp.get("odds", 0) >= 1.05:
            candidates.append({**sp, "fixture": m["fixture"], "kickoff": m.get("kickoff")})
        if bp and bp.get("odds", 0) >= 1.05:
            candidates.append({**bp, "fixture": m["fixture"], "kickoff": m.get("kickoff")})

    if not candidates:
        return f"⚠️ *No eligible betting options available for {slip_name}.*"

    # Strategy filtering & ranking
    if strategy == "banker":
        pool = [c for c in candidates if c.get("prob", 0) >= 0.70 and c.get("odds", 0) >= 1.10]
        pool.sort(key=lambda x: (x["prob"], x["odds"]), reverse=True)
    elif strategy == "risky":
        # Underdog value, draw trends, or high odds (>= 2.10)
        pool = [c for c in candidates if c.get("odds", 0) >= 2.00]
        if not pool:
            pool = [c for c in candidates if c.get("odds", 0) >= 1.60]
        pool.sort(key=lambda x: (x.get("ev", 0) or 0, x["odds"]), reverse=True)
    elif strategy == "mega":
        # 100x target: balance high probability and solid odds
        pool = [c for c in candidates if c.get("odds", 0) >= 1.15 and c.get("prob", 0) >= 0.55]
        pool.sort(key=lambda x: (x["prob"], x["odds"]), reverse=True)
    else:  # balanced or sharp
        pool = [c for c in candidates if c.get("odds", 0) >= 1.12 and c.get("prob", 0) >= 0.60]
        pool.sort(key=lambda x: (x["prob"], x["odds"]), reverse=True)

    # Greedily combine legs without duplicating matches
    selected_legs: list[dict[str, Any]] = []
    seen_fixtures: set[str] = set()
    current_odds = 1.0

    for leg in pool:
        fix = leg["fixture"]
        if fix in seen_fixtures:
            continue
        leg_odds = leg["odds"]
        if current_odds >= target_odds and len(selected_legs) >= 2:
            break
        selected_legs.append(leg)
        seen_fixtures.add(fix)
        current_odds *= leg_odds

    if not selected_legs:
        return f"⚠️ *Could not construct {slip_name} with today's fixture list.*"

    combined_odds = round(current_odds, 2)

    # Attempt to book ticket directly on official SportyBet order API
    booking_selections = []
    for leg in selected_legs:
        ev_id = leg.get("event_id")
        m_id = leg.get("market_id")
        oc_id = leg.get("outcome_id")
        spec = leg.get("specifier")
        if ev_id and m_id and oc_id:
            booking_selections.append({
                "eventId": str(ev_id),
                "marketId": str(m_id),
                "outcomeId": str(oc_id),
                "specifier": spec if spec else None,
            })

    booking_code = None
    share_url = None

    if len(booking_selections) == len(selected_legs):
        try:
            res = await asyncio.to_thread(generate_real_sportybet_booking_code, booking_selections)
            if res.get("success"):
                booking_code = res.get("share_code")
                share_url = res.get("share_url")
        except Exception:
            pass

    # Build formatted Telegram message
    today_str = datetime.now(ZoneInfo("Africa/Lagos")).strftime("%d %b %Y")
    lines = [
        f"📋 *{slip_name.upper()}* ({today_str})\n"
        f"💰 *Total Odds:* `{combined_odds:.2f}x` | *Legs:* `{len(selected_legs)}`\n"
    ]

    for i, leg in enumerate(selected_legs, 1):
        lines.append(
            f"{i}. *{leg['fixture']}*\n"
            f"   👉 `{leg['market']}: {leg['selection']}` @ *{leg['odds']:.2f}* "
            f"(P: {leg['prob'] * 100:.0f}%)"
        )

    if booking_code:
        lines.append(f"\n🔥 *SportyBet Booking Code:* `{booking_code}`")
        if share_url:
            lines.append(f"🔗 [Load Slip Directly on SportyBet.com]({share_url})")
    else:
        lines.append("\n⚠️ _Live SportyBet booking code generation temporarily busy; selections shown above._")

    return "\n".join(lines)
