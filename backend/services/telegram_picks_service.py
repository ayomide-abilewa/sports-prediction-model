from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from backend.api.predictions import _build_sporty_match_item, _get_fitted_model
from backend.db.engine import AsyncSessionLocal
from backend.ingestion.sportybet_service import (
    fetch_sporty_upcoming_events,
    generate_real_sportybet_booking_code,
)
from backend.services.audit_service import build_audit_report

# Cache today's matches in memory (refresh every 5 minutes)
_TODAY_CACHE: dict[str, Any] = {
    "timestamp": 0.0,
    "date": None,
    "items": [],
}

# In-memory builder sessions for interactive betslip creation per chat_id
BUILDER_SESSIONS: dict[int | str, dict[str, Any]] = {}


def club_league_priority(fixture: str, league: str) -> int:
    """Scores matches so top European elite clubs and major leagues always appear first."""
    text = f"{fixture} {league}".casefold()

    # Priority 0: Elite European powerhouses
    elite = (
        "real madrid", "barcelona", "bayern", "psg", "paris", "arsenal",
        "man city", "man united", "liverpool", "chelsea", "inter", "milan",
        "juventus", "napoli", "dortmund", "leverkusen", "atletico", "tottenham",
        "celtic", "rangers", "sporting", "benfica", "porto", "ajax", "feyenoord",
    )
    if any(c in text for c in elite):
        return 0

    # Priority 1: Top European domestic & continental competitions
    top_competitions = (
        "champions league", "europa league", "conference league",
        "premier league", "la liga", "laliga", "serie a", "bundesliga", "ligue 1",
    )
    if any(comp in text for comp in top_competitions):
        return 1

    # Priority 2: Major secondary leagues and domestic cups
    mid_competitions = (
        "premiership", "eredivisie", "championship", "copa del rey",
        "dfb pokal", "league cup", "coppa italia", "brasileiro", "primeira liga",
        "uefa youth", "allsvenskan", "knvb beker",
    )
    if any(comp in text for comp in mid_competitions):
        return 2

    return 3


def refine_smart_picks(match_item: dict[str, Any]) -> dict[str, Any]:
    """Ensures Main Pick has real betting meat (odds >= 1.25) and Prop is meaningful (odds >= 1.35)."""
    markets = match_item.get("markets", [])
    if not markets:
        return match_item

    # 1. Main Pick: Prefer high-conviction 1X2, Double Chance, Team Goals, or Match Goals with odds >= 1.25
    eligible_main = [
        p for p in markets
        if p.get("odds", 0) >= 1.22 and p.get("probability", 0) >= 0.48
    ]

    if eligible_main:
        # Score prioritizing probability * (odds^0.55), with bonus for 1X2, DC, and Team Goals
        def main_score(p: dict[str, Any]) -> float:
            prob = p.get("probability", 0)
            odds = p.get("odds", 1.0)
            m_type = p.get("market", "").casefold()
            boost = 1.15 if any(k in m_type for k in ("double chance", "1x2", "team goals", "gg")) else 1.0
            return (prob >= 0.65) * 1.5 + (prob * (odds ** 0.55)) * boost

        eligible_main.sort(key=main_score, reverse=True)
        best_main = eligible_main[0]
        match_item["surest_prediction"] = {
            "market": best_main["market"],
            "selection": best_main["selection"],
            "odds": best_main["odds"],
            "prob": best_main["probability"],
            "event_id": best_main.get("event_id"),
            "market_id": best_main.get("market_id"),
            "outcome_id": best_main.get("outcome_id"),
            "specifier": best_main.get("specifier"),
        }

    # 2. Best Prop: Corners, Cards, or 1H Goals with odds >= 1.35
    sp = match_item.get("surest_prediction") or {}
    eligible_props = [
        p for p in markets
        if p.get("odds", 0) >= 1.30
        and (p.get("market") != sp.get("market") or p.get("selection") != sp.get("selection"))
    ]

    if eligible_props:
        def prop_score(p: dict[str, Any]) -> tuple[bool, float]:
            m_type = p.get("market", "").casefold()
            is_special = any(k in m_type for k in ("corner", "card", "booking", "half", "clean sheet"))
            prob = p.get("probability", 0)
            odds = p.get("odds", 1.0)
            return (is_special, prob * (odds ** 0.5))

        eligible_props.sort(key=prop_score, reverse=True)
        best_prop = eligible_props[0]
        match_item["best_prop"] = {
            "market": best_prop["market"],
            "selection": best_prop["selection"],
            "odds": best_prop["odds"],
            "prob": best_prop["probability"],
            "event_id": best_prop.get("event_id"),
            "market_id": best_prop.get("market_id"),
            "outcome_id": best_prop.get("outcome_id"),
            "specifier": best_prop.get("specifier"),
        }

    return match_item


async def get_today_matches(force_refresh: bool = False) -> list[dict[str, Any]]:
    """Returns today's active unplayed matches ranked by elite clubs and major leagues."""
    now_utc = datetime.now(timezone.utc)
    target_date = datetime.now(ZoneInfo("Africa/Lagos")).date()

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
                item = refine_smart_picks(item)
                today_items.append(item)

    # Sort today's items: Elite clubs and top leagues first, then by kickoff time
    today_items.sort(key=lambda x: (
        club_league_priority(x.get("fixture", ""), x.get("league", "")),
        x.get("kickoff", ""),
    ))

    _TODAY_CACHE["timestamp"] = time.time()
    _TODAY_CACHE["date"] = target_date
    _TODAY_CACHE["items"] = today_items
    return today_items


def format_paginated_fixtures(
    matches: list[dict[str, Any]], page: int = 0, page_size: int = 10
) -> tuple[str, dict[str, Any]]:
    """Formats today's fixtures with inline keyboard pagination so user can browse all games."""
    if not matches:
        return "📅 *No upcoming scheduled fixtures remaining for today.*", {}

    total_matches = len(matches)
    total_pages = max(1, (total_matches + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))

    start = page * page_size
    end = min(start + page_size, total_matches)
    subset = matches[start:end]

    today_str = datetime.now(ZoneInfo("Africa/Lagos")).strftime("%A, %d %B %Y")
    lines = [
        f"📅 *Today's Football Schedule ({today_str})*\n"
        f"_Showing matches {start + 1}–{end} of {total_matches} (Elite clubs first):_\n"
    ]

    for i, m in enumerate(subset, start=start + 1):
        try:
            kick_dt = datetime.fromisoformat(m["kickoff"].replace("Z", "+00:00")).astimezone(
                ZoneInfo("Africa/Lagos")
            )
            time_display = kick_dt.strftime("%H:%M WAT")
        except Exception:
            time_display = "TBD"

        league = m.get("league", "Football")
        lines.append(f"{i}. *{m['fixture']}*\n   🏆 `{league}` | 🕒 `{time_display}`")

    # Build pagination buttons
    buttons = []
    nav_row = []
    if page > 0:
        nav_row.append({"text": "⬅️ Prev", "callback_data": f"fix_page:{page - 1}"})
    nav_row.append({"text": f"📄 {page + 1}/{total_pages}", "callback_data": "noop"})
    if page < total_pages - 1:
        nav_row.append({"text": "Next ➡️", "callback_data": f"fix_page:{page + 1}"})

    if nav_row:
        buttons.append(nav_row)

    buttons.append([
        {"text": "🎯 View Predictions", "callback_data": f"pred_page:{page}"},
        {"text": "🎫 Build 2x Slip", "callback_data": "build_start:2"},
    ])

    return "\n".join(lines), {"inline_keyboard": buttons}


def format_paginated_predictions(
    matches: list[dict[str, Any]], page: int = 0, page_size: int = 6
) -> tuple[str, dict[str, Any]]:
    """Formats today's predictions (Surest Pick & Best Prop) with inline pagination."""
    if not matches:
        return "🎯 *No match predictions available for today's schedule yet.*", {}

    total_matches = len(matches)
    total_pages = max(1, (total_matches + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))

    start = page * page_size
    end = min(start + page_size, total_matches)
    subset = matches[start:end]

    today_str = datetime.now(ZoneInfo("Africa/Lagos")).strftime("%A, %d %b")
    lines = [
        f"🎯 *MATCHDAY PREDICTIONS — {today_str}*\n"
        f"_Matches {start + 1}–{end} of {total_matches} (Big Clubs & Top Leagues First):_\n"
    ]

    for i, m in enumerate(subset, start=start + 1):
        try:
            kick_dt = datetime.fromisoformat(m["kickoff"].replace("Z", "+00:00")).astimezone(
                ZoneInfo("Africa/Lagos")
            )
            time_display = kick_dt.strftime("%H:%M WAT")
        except Exception:
            time_display = "TBD"

        league = m.get("league", "League")
        sp = m.get("surest_prediction") or {}
        bp = m.get("best_prop") or {}

        sp_text = (
            f"   🎯 *Main:* `{sp.get('market')}: {sp.get('selection')}` @ *{sp.get('odds', 1.0):.2f}* "
            f"({sp.get('prob', 0.0) * 100:.0f}%)"
            if sp
            else "   🎯 *Main:* Pending"
        )
        bp_text = (
            f"   🔥 *Prop:* `{bp.get('market')}: {bp.get('selection')}` @ *{bp.get('odds', 1.0):.2f}* "
            f"({bp.get('prob', 0.0) * 100:.0f}%)"
            if bp
            else "   🔥 *Prop:* Neutral line"
        )

        lines.append(f"{i}. *{m['fixture']}* (🏆 `{league}` | 🕒 `{time_display}`)\n{sp_text}\n{bp_text}\n")

    # Pagination navigation
    buttons = []
    nav_row = []
    if page > 0:
        nav_row.append({"text": "⬅️ Prev", "callback_data": f"pred_page:{page - 1}"})
    nav_row.append({"text": f"📄 {page + 1}/{total_pages}", "callback_data": "noop"})
    if page < total_pages - 1:
        nav_row.append({"text": "Next ➡️", "callback_data": f"pred_page:{page + 1}"})

    if nav_row:
        buttons.append(nav_row)

    buttons.append([
        {"text": "🎫 Build 2x Slip", "callback_data": "build_start:2"},
        {"text": "💎 Build 5x Slip", "callback_data": "build_start:5"},
    ])

    return "\n".join(lines), {"inline_keyboard": buttons}


def format_bankers_text(matches: list[dict[str, Any]]) -> str:
    """Filters highest-probability banker selections for today with solid odds."""
    bankers = []
    for m in matches:
        sp = m.get("surest_prediction")
        if sp and sp.get("prob", 0) >= 0.65 and sp.get("odds", 0) >= 1.20:
            bankers.append((m, sp))

    bankers.sort(key=lambda item: (item[1]["prob"] >= 0.70, item[1]["prob"] * item[1]["odds"]), reverse=True)

    if not bankers:
        return "🔒 *No Tier-1 Banker selections (≥65% probability & odds ≥1.20) found for remaining games today.*"

    today_str = datetime.now(ZoneInfo("Africa/Lagos")).strftime("%A, %d %b")
    lines = [f"🔒 *TIER 1 BANKERS — {today_str}*\n_Top probability mathematically validated value picks:_\n"]

    for i, (m, sp) in enumerate(bankers[:7], 1):
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
            f"   📊 Probability: *{sp['prob'] * 100:.1f}%* | Status: `High Value`\n"
        )

    lines.append("🎫 *Tap '2x Banker Slip' below to generate a verified booking code with these picks!*")
    return "\n".join(lines)


# =========================================================================
# INTERACTIVE SLIP BUILDER (STEP-BY-STEP USER SELECTION)
# =========================================================================

def start_builder_session(
    chat_id: int | str,
    target_odds: float,
    slip_name: str,
    matches: list[dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    """Starts a step-by-step interactive betslip builder session."""
    BUILDER_SESSIONS[chat_id] = {
        "target_odds": target_odds,
        "slip_name": slip_name,
        "match_idx": 0,
        "legs": [],
        "current_odds": 1.0,
        "matches": matches,
    }
    return render_builder_step(chat_id)


def render_builder_step(chat_id: int | str) -> tuple[str, dict[str, Any]]:
    """Renders the current match step with Main and Prop interactive selection buttons."""
    session = BUILDER_SESSIONS.get(chat_id)
    if not session:
        return "⚠️ *Slip builder expired. Please choose an option from the menu.*", {}

    matches = session["matches"]
    idx = session["match_idx"]
    current_odds = session["current_odds"]
    target = session["target_odds"]
    legs = session["legs"]
    slip_name = session["slip_name"]

    # Check if target odds reached or all matches evaluated
    if (current_odds >= target and len(legs) >= 1) or idx >= len(matches):
        return None, None  # Signals completion!

    match = matches[idx]
    sp = match.get("surest_prediction") or {}
    bp = match.get("best_prop") or {}

    try:
        kick_dt = datetime.fromisoformat(match["kickoff"].replace("Z", "+00:00")).astimezone(
            ZoneInfo("Africa/Lagos")
        )
        time_display = kick_dt.strftime("%H:%M WAT")
    except Exception:
        time_display = "TBD"

    # Progress bar visualization
    pct = min(1.0, current_odds / max(target, 1.01))
    bar_len = 10
    filled = int(pct * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)

    lines = [
        f"🎫 *{slip_name.upper()} BUILDER (Match {idx + 1}/{len(matches)})*\n"
        f"📊 *Progress:* `[{bar}]` *{current_odds:.2f}x / {target:.1f}x* ({len(legs)} legs)\n"
    ]

    if legs:
        lines.append("*Current Selections:*")
        for i, leg in enumerate(legs, 1):
            lines.append(f"  ✅ {i}. {leg['fixture']} — `{leg['selection']}` @ *{leg['odds']:.2f}*")
        lines.append("")

    lines.append(f"⚽ *{match['fixture']}* (🏆 `{match.get('league')}` | 🕒 `{time_display}`)\n")
    lines.append(f"🎯 *Main Pick:* `{sp.get('market')}: {sp.get('selection')}` @ *{sp.get('odds', 1.0):.2f}* ({sp.get('prob', 0) * 100:.0f}%)")
    lines.append(f"🔥 *Best Prop:* `{bp.get('market')}: {bp.get('selection')}` @ *{bp.get('odds', 1.0):.2f}* ({bp.get('prob', 0) * 100:.0f}%)\n")
    lines.append("👉 *Select an option below to add to your slip:*")

    buttons = [
        [
            {"text": f"🎯 Pick Main (@{sp.get('odds', 1.0):.2f})", "callback_data": f"bld_pick:main:{idx}"},
            {"text": f"🔥 Pick Prop (@{bp.get('odds', 1.0):.2f})", "callback_data": f"bld_pick:prop:{idx}"},
        ],
        [
            {"text": "⏭️ Skip Match", "callback_data": f"bld_skip:{idx}"},
            {"text": "⚡ Auto-Finish Slip", "callback_data": "bld_autofinish"},
        ],
    ]

    if legs:
        buttons.append([
            {"text": f"🏁 Finish Now ({current_odds:.2f}x)", "callback_data": "bld_finish_now"}
        ])

    return "\n".join(lines), {"inline_keyboard": buttons}


async def handle_builder_choice(
    chat_id: int | str, choice: str, match_idx_str: str = "0"
) -> tuple[str, dict[str, Any]]:
    """Handles user button click (Pick Main, Pick Prop, Skip, Auto-Finish, Finish Now)."""
    session = BUILDER_SESSIONS.get(chat_id)
    if not session:
        return "⚠️ *Slip builder expired. Please choose an option from the menu.*", {}

    matches = session["matches"]
    idx = session["match_idx"]

    if choice in ("main", "prop") and idx < len(matches):
        match = matches[idx]
        pick = match.get("surest_prediction") if choice == "main" else match.get("best_prop")
        if pick and pick.get("odds", 0) > 1.0:
            session["legs"].append({**pick, "fixture": match["fixture"]})
            session["current_odds"] = round(session["current_odds"] * pick["odds"], 2)
        session["match_idx"] += 1

    elif choice == "skip":
        session["match_idx"] += 1

    elif choice == "autofinish":
        # Automatically select the best remaining legs to reach the target odds
        target = session["target_odds"]
        while session["current_odds"] < target and session["match_idx"] < len(matches):
            m = matches[session["match_idx"]]
            sp = m.get("surest_prediction")
            if sp and sp.get("odds", 0) >= 1.15:
                session["legs"].append({**sp, "fixture": m["fixture"]})
                session["current_odds"] = round(session["current_odds"] * sp["odds"], 2)
            session["match_idx"] += 1
        return await finalize_builder_slip(chat_id)

    elif choice == "finish_now":
        return await finalize_builder_slip(chat_id)

    # Check if target odds reached
    if session["current_odds"] >= session["target_odds"] and len(session["legs"]) >= 1:
        return await finalize_builder_slip(chat_id)

    # Render next match step
    text, markup = render_builder_step(chat_id)
    if text is None:
        return await finalize_builder_slip(chat_id)

    return text, markup


async def finalize_builder_slip(chat_id: int | str) -> tuple[str, dict[str, Any]]:
    """Submits selections directly to SportyBet and presents the completed booking ticket."""
    session = BUILDER_SESSIONS.pop(chat_id, None)
    if not session or not session.get("legs"):
        return "⚠️ *No legs were selected for this slip.*", {}

    legs = session["legs"]
    combined_odds = session["current_odds"]
    slip_name = session["slip_name"]

    # Book with SportyBet official API
    booking_selections = []
    for leg in legs:
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

    if len(booking_selections) == len(legs):
        try:
            res = await asyncio.to_thread(generate_real_sportybet_booking_code, booking_selections)
            if res.get("success"):
                booking_code = res.get("share_code")
                share_url = res.get("share_url")
        except Exception:
            pass

    today_str = datetime.now(ZoneInfo("Africa/Lagos")).strftime("%d %b %Y")
    lines = [
        f"🎉 *YOUR {slip_name.upper()} IS READY!* ({today_str})\n"
        f"💰 *Total Odds:* `{combined_odds:.2f}x` | *Legs:* `{len(legs)}`\n"
    ]

    for i, leg in enumerate(legs, 1):
        lines.append(
            f"{i}. *{leg['fixture']}*\n"
            f"   👉 `{leg['market']}: {leg['selection']}` @ *{leg['odds']:.2f}* "
            f"(P: {leg.get('prob', 0.5) * 100:.0f}%)"
        )

    if booking_code:
        lines.append(f"\n🔥 *SportyBet Booking Code:* `{booking_code}`")
        if share_url:
            lines.append(f"🔗 [Click Here to Load Directly on SportyBet]({share_url})")
    else:
        lines.append("\n⚠️ _Live SportyBet booking service temporarily busy; your selections are detailed above._")

    lines.append("\n💡 *Tap any button below to start building another slip!*")

    # Give buttons to quickly build another slip or view predictions
    buttons = [
        [
            {"text": "🎫 Build 2x Slip", "callback_data": "build_start:2"},
            {"text": "💎 Build 5x Slip", "callback_data": "build_start:5"},
        ],
        [
            {"text": "⚡ Build 15x Slip", "callback_data": "build_start:15"},
            {"text": "💯 Build 100x Slip", "callback_data": "build_start:100"},
        ],
    ]

    return "\n".join(lines), {"inline_keyboard": buttons}


async def auto_generate_slip(
    matches: list[dict[str, Any]],
    slip_name: str,
    target_odds: float,
    strategy: str = "balanced",
) -> tuple[str, dict[str, Any]]:
    """Instant one-click accumulator slip generator with SportyBet booking code."""
    if not matches:
        return f"⚠️ *No matches available today for {slip_name}.*", {}

    candidates: list[dict[str, Any]] = []
    for m in matches:
        sp = m.get("surest_prediction")
        bp = m.get("best_prop")
        if sp and sp.get("odds", 0) >= 1.15:
            candidates.append({**sp, "fixture": m["fixture"]})
        if bp and bp.get("odds", 0) >= 1.30:
            candidates.append({**bp, "fixture": m["fixture"]})

    if not candidates:
        return f"⚠️ *No verified betting options available today for {slip_name}.*", {}

    if strategy == "banker":
        pool = [c for c in candidates if c.get("prob", 0) >= 0.70 and c.get("odds", 0) >= 1.20]
        pool.sort(key=lambda x: (x["prob"], x["odds"]), reverse=True)
    elif strategy == "risky":
        pool = [c for c in candidates if c.get("odds", 0) >= 2.00]
        if not pool:
            pool = [c for c in candidates if c.get("odds", 0) >= 1.60]
        pool.sort(key=lambda x: (x.get("ev", 0) or 0, x["odds"]), reverse=True)
    elif strategy == "mega":
        pool = [c for c in candidates if c.get("odds", 0) >= 1.20 and c.get("prob", 0) >= 0.55]
        pool.sort(key=lambda x: (x["prob"], x["odds"]), reverse=True)
    else:
        pool = [c for c in candidates if c.get("odds", 0) >= 1.20 and c.get("prob", 0) >= 0.60]
        pool.sort(key=lambda x: (x["prob"], x["odds"]), reverse=True)

    selected_legs: list[dict[str, Any]] = []
    seen: set[str] = set()
    odds = 1.0

    for leg in pool:
        fix = leg["fixture"]
        if fix in seen:
            continue
        if odds >= target_odds and len(selected_legs) >= 2:
            break
        selected_legs.append(leg)
        seen.add(fix)
        odds *= leg["odds"]

    combined_odds = round(odds, 2)

    # Book with SportyBet
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

    today_str = datetime.now(ZoneInfo("Africa/Lagos")).strftime("%d %b %Y")
    lines = [
        f"📋 *{slip_name.upper()}* ({today_str})\n"
        f"💰 *Total Odds:* `{combined_odds:.2f}x` | *Legs:* `{len(selected_legs)}`\n"
    ]

    for i, leg in enumerate(selected_legs, 1):
        lines.append(
            f"{i}. *{leg['fixture']}*\n"
            f"   👉 `{leg['market']}: {leg['selection']}` @ *{leg['odds']:.2f}* "
            f"(P: {leg.get('prob', 0.5) * 100:.0f}%)"
        )

    if booking_code:
        lines.append(f"\n🔥 *SportyBet Booking Code:* `{booking_code}`")
        if share_url:
            lines.append(f"🔗 [Load Slip Directly on SportyBet.com]({share_url})")

    # Give an interactive builder option
    builder_param = "2" if target_odds <= 3.0 else ("5" if target_odds <= 8.0 else ("15" if target_odds <= 25.0 else "100"))
    buttons = [
        [{"text": f"🛠️ Build Custom {builder_param}x Match-by-Match", "callback_data": f"build_start:{builder_param}"}]
    ]

    return "\n".join(lines), {"inline_keyboard": buttons}
