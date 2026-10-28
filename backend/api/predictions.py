from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any
import zlib
from fastapi import APIRouter, Depends, Query
import pandas as pd
from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.betting.confidence import ConfidenceClassifier
from backend.db.engine import get_db
from backend.models.league import Season
from backend.models.match import Match
from backend.models.odds import MarketOdds
from backend.models.prediction import ModelVersion, Prediction
from backend.services.sportybet_persistence import sporty_league_code
from backend.probability.dixon_coles import DixonColesModel
from backend.probability.markets import MarketEngine
from backend.ingestion.sportybet_service import (
    fetch_sporty_upcoming_events,
    fetch_sporty_event_detail,
    parse_sporty_markets,
)
from backend.ingestion.team_mapper import team_mapper

router = APIRouter(prefix="/predictions", tags=["Predictions"])
classifier = ConfidenceClassifier(min_ev_threshold=-0.05)


def generate_ai_rationale(
    home: str,
    away: str,
    market: str,
    selection: str,
    prob: float,
    pred: dict[str, Any],
    probability_source: str = "model",
) -> str:
    """Generates an intuitive analytical summary explaining why the AI recommends this pick."""
    if probability_source == "market":
        return (
            f"The available market prices imply {prob * 100:.1f}% for {selection} after removing "
            "the bookmaker margin. Team-specific model coverage is unavailable for this fixture."
        )
    if not pred:
        return "No team-specific historical model estimate is available for this fixture."
    exp = pred.get("expected_goals", {})
    exp_h = exp.get("home", 1.4)
    exp_a = exp.get("away", 1.1)
    tot = exp.get("total", 2.5)

    if market == "1X2":
        if "to Win (1)" in selection or selection.lower() == "home":
            return f"{home} carries superior attacking firepower ({exp_h} xG) against {away}'s defensive structure. Model assigns a strong {prob * 100:.1f}% home win conviction."
        elif "to Win (2)" in selection or selection.lower() == "away":
            return f"{away} holds a clinical offensive edge ({exp_a} xG) capable of breaching {home}'s backline with a {prob * 100:.1f}% away win edge."
        return f"Evenly matched tactical contest. Both sides project balanced ratings, establishing a {prob * 100:.1f}% draw probability."

    elif market == "Double Chance":
        return f"{selection} covers two of the three match outcomes. The estimated probability is {prob * 100:.1f}%."

    elif market == "Draw No Bet":
        return f"Eliminating the draw outcome gives {selection} a decisive mathematical edge at {prob * 100:.1f}% confidence."

    elif market == "GG / NG":
        return f"The forecast assigns {prob * 100:.1f}% probability to {selection}."

    elif market == "Match Goals":
        if "Over" in selection:
            return f"Projected combined goal expectation of {tot} xG. High chance of goals flowing freely from both forward lines ({prob * 100:.1f}% probability)."
        return f"Defensive stability and low transitional tempo project a tight contest staying under the goal line ({prob * 100:.1f}% probability)."

    elif market == "Team Goals":
        return f"The goal model assigns {prob * 100:.1f}% probability to {selection}."

    elif market == "Clean Sheet":
        return f"The forecast assigns {prob * 100:.1f}% probability to {selection}."

    elif market == "Handicap":
        return f"Margin-of-victory distribution projects favorable spread coverage for {selection} at {prob * 100:.1f}% probability."

    elif market == "Corners":
        return f"The available corner market prices imply {prob * 100:.1f}% for {selection}."

    elif market == "Cards & Bookings":
        return f"The available card market prices imply {prob * 100:.1f}% for {selection}."

    return f"Statistical Poisson model establishes a {prob * 100:.1f}% mathematical probability based on historical ratings."


async def _get_fitted_model(db: AsyncSession) -> DixonColesModel | None:
    """Trains a Dixon-Coles model on recent historical finished fixtures."""
    hist_stmt = (
        select(Match)
        .options(selectinload(Match.home_team), selectinload(Match.away_team))
        .where(Match.status == "finished")
        .order_by(desc(Match.kickoff))
        .limit(200)
    )
    hist_res = await db.execute(hist_stmt)
    hist_matches = hist_res.scalars().all()

    if not hist_matches:
        return None

    df_data = [
        {
            "home_team": m.home_team.name,
            "away_team": m.away_team.name,
            "ft_home_goals": m.ft_home_goals,
            "ft_away_goals": m.ft_away_goals,
            "kickoff": m.kickoff,
        }
        for m in hist_matches
    ]
    dc = DixonColesModel()
    try:
        dc.fit(pd.DataFrame(df_data))
        dc.training_sample_count = len(df_data)
        return dc
    except Exception:
        return None


def _build_sporty_match_item(ev: dict[str, Any], dc: DixonColesModel | None) -> dict[str, Any] | None:
    eid = ev.get("eventId")
    home = ev.get("homeTeamName")
    away = ev.get("awayTeamName")
    if not home or not away or not eid:
        return None

    home, _ = team_mapper.resolve(str(home))
    away, _ = team_mapper.resolve(str(away))

    sport = ev.get("sport", {})
    category = sport.get("category", {}) if isinstance(sport, dict) else {}
    tournament = category.get("tournament", {}) if isinstance(category, dict) else {}
    cat_name = category.get("name", "") if isinstance(category, dict) else ""
    tourn_name = tournament.get("name", "") if isinstance(tournament, dict) else ""
    cat_name = cat_name or ev.get("categoryName", "")
    tournament_meta = ev.get("tournament", {})
    tournament_fallback = tournament_meta.get("name", "") if isinstance(tournament_meta, dict) else str(tournament_meta or "")
    tourn_name = tourn_name or ev.get("tournamentName", "") or tournament_fallback
    league_name = f"{tourn_name}" if tourn_name else (cat_name or "SportyBet Top League")

    start_ts = ev.get("estimateStartTime")
    kickoff_dt = (
        datetime.fromtimestamp(start_ts / 1000.0, tz=timezone.utc)
        if start_ts
        else datetime.now(timezone.utc)
    )

    parsed = parse_sporty_markets(ev)

    try:
        team_history = dc is not None and home in dc.team_idx and away in dc.team_idx
        pred = dc.predict_match(home, away) if team_history else {}
    except Exception:
        pred = {}

    exp_goals = pred.get("expected_goals")

    grouped_options: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for options in parsed.values():
        for option in options:
            key = (str(option.get("market_id")), str(option.get("specifier") or ""))
            grouped_options.setdefault(key, []).append(option)

    market_probabilities: dict[tuple[str, str, str], float] = {}
    for (market_id, specifier), options in grouped_options.items():
        valid = [option for option in options if option.get("odds", 0) > 1.0]
        implied = [1.0 / option["odds"] for option in valid]
        total = sum(implied)
        if len(valid) >= 2 and total > 0:
            for option, probability in zip(valid, implied):
                market_probabilities[(market_id, specifier, str(option.get("outcome_id")))] = probability / total

    def get_probability(option: dict[str, Any], model_probability: float | None = None) -> tuple[float, str] | None:
        if model_probability is not None and 0.0 < model_probability < 1.0:
            return model_probability, "model"
        key = (str(option.get("market_id")), str(option.get("specifier") or ""), str(option.get("outcome_id")))
        probability = market_probabilities.get(key)
        return (probability, "market") if probability is not None else None

    evaluated_picks: list[dict[str, Any]] = []

    # 1. 1X2
    for opt in parsed["one_x_two"]:
        sel = opt["selection"]
        result_key = sel.casefold().strip()
        if result_key in {"1", "home", home.casefold()}:
            result_key = "home"
        elif result_key in {"x", "draw"}:
            result_key = "draw"
        elif result_key in {"2", "away", away.casefold()}:
            result_key = "away"
        estimate = get_probability(opt, pred.get("1x2", {}).get(result_key))
        if not estimate:
            continue
        prob, prob_source = estimate
        evaluated_picks.append({
            "market_type": "1X2",
            "selection": f"{sel} to Win" if sel in ["Home", "Away"] else sel,
            "model_probability": round(prob, 4),
            "fair_odds": round(1.0 / max(prob, 0.01), 2),
            "available_odds": opt["odds"],
            "expected_value": round((prob * opt["odds"]) - 1.0, 4),
            "confidence_tier": "Model estimate" if prob_source == "model" else "Market implied",
            "ai_rationale": generate_ai_rationale(home, away, "1X2", sel, prob, pred, prob_source),
            "event_id": eid,
            "market_id": opt["market_id"],
            "outcome_id": opt["outcome_id"],
            "specifier": opt["specifier"],
            "probability_source": prob_source,
        })

    # 2. Double Chance
    for opt in parsed["double_chance"]:
        sel = opt["selection"]
        lower_sel = sel.casefold()
        model_key = "1x" if "1x" in lower_sel or "home or draw" in lower_sel else (
            "x2" if "x2" in lower_sel or "draw or away" in lower_sel else "12"
        )
        model_probability = pred.get("double_chance", {}).get(model_key)
        estimate = get_probability(opt, model_probability)
        if not estimate:
            continue
        prob, prob_source = estimate
        evaluated_picks.append({
            "market_type": "Double Chance",
            "selection": sel,
            "model_probability": round(prob, 4),
            "fair_odds": round(1.0 / max(prob, 0.01), 2),
            "available_odds": opt["odds"],
            "expected_value": round((prob * opt["odds"]) - 1.0, 4),
            "confidence_tier": "Model estimate" if prob_source == "model" else "Market implied",
            "ai_rationale": generate_ai_rationale(home, away, "Double Chance", sel, prob, pred, prob_source),
            "event_id": eid,
            "market_id": opt["market_id"],
            "outcome_id": opt["outcome_id"],
            "specifier": opt["specifier"],
            "probability_source": prob_source,
        })

    # 3. Over / Under Goals
    for opt in parsed["goals_over_under"]:
        sel = opt["selection"]
        tot = opt.get("total", "2.5")
        ou_map = pred.get("totals", {}).get(f"over_under_{tot}", {})
        model_key = "over" if "over" in sel.casefold() else "under"
        estimate = get_probability(opt, ou_map.get(model_key))
        if not estimate:
            continue
        prob, prob_source = estimate

        evaluated_picks.append({
            "market_type": "Match Goals",
            "selection": sel,
            "model_probability": round(prob, 4),
            "fair_odds": round(1.0 / max(prob, 0.01), 2),
            "available_odds": opt["odds"],
            "expected_value": round((prob * opt["odds"]) - 1.0, 4),
            "confidence_tier": "Model estimate" if prob_source == "model" else "Market implied",
            "ai_rationale": generate_ai_rationale(home, away, "Match Goals", sel, prob, pred, prob_source),
            "event_id": eid,
            "market_id": opt["market_id"],
            "outcome_id": opt["outcome_id"],
            "specifier": opt["specifier"],
            "probability_source": prob_source,
        })

    # 4. GG / NG
    for opt in parsed["both_teams_to_score"]:
        sel = opt["selection"]
        model_key = "yes" if sel.casefold() in {"yes", "gg"} else "no"
        estimate = get_probability(opt, pred.get("btts", {}).get(model_key))
        if not estimate:
            continue
        prob, prob_source = estimate
        evaluated_picks.append({
            "market_type": "GG / NG",
            "selection": f"Both Teams To Score ({sel})",
            "model_probability": round(prob, 4),
            "fair_odds": round(1.0 / max(prob, 0.01), 2),
            "available_odds": opt["odds"],
            "expected_value": round((prob * opt["odds"]) - 1.0, 4),
            "confidence_tier": "Model estimate" if prob_source == "model" else "Market implied",
            "ai_rationale": generate_ai_rationale(home, away, "GG / NG", sel, prob, pred, prob_source),
            "event_id": eid,
            "market_id": opt["market_id"],
            "outcome_id": opt["outcome_id"],
            "specifier": opt["specifier"],
            "probability_source": prob_source,
        })

    # 5. Corners
    for opt in parsed["corners"]:
        sel = opt["selection"]
        estimate = get_probability(opt)
        if not estimate:
            continue
        prob, prob_source = estimate
        evaluated_picks.append({
            "market_type": "Corners",
            "selection": sel,
            "model_probability": round(prob, 4),
            "fair_odds": round(1.0 / max(prob, 0.01), 2),
            "available_odds": opt["odds"],
            "expected_value": round((prob * opt["odds"]) - 1.0, 4),
            "confidence_tier": "Model estimate" if prob_source == "model" else "Market implied",
            "ai_rationale": generate_ai_rationale(home, away, "Corners", sel, prob, pred, prob_source),
            "event_id": eid,
            "market_id": opt["market_id"],
            "outcome_id": opt["outcome_id"],
            "specifier": opt["specifier"],
            "probability_source": prob_source,
        })

    # 6. Cards & Bookings
    for opt in parsed["cards"]:
        sel = opt["selection"]
        estimate = get_probability(opt)
        if not estimate:
            continue
        prob, prob_source = estimate
        evaluated_picks.append({
            "market_type": "Cards & Bookings",
            "selection": sel,
            "model_probability": round(prob, 4),
            "fair_odds": round(1.0 / max(prob, 0.01), 2),
            "available_odds": opt["odds"],
            "expected_value": round((prob * opt["odds"]) - 1.0, 4),
            "confidence_tier": "Model estimate" if prob_source == "model" else "Market implied",
            "ai_rationale": generate_ai_rationale(home, away, "Cards & Bookings", sel, prob, pred, prob_source),
            "event_id": eid,
            "market_id": opt["market_id"],
            "outcome_id": opt["outcome_id"],
            "specifier": opt["specifier"],
            "probability_source": prob_source,
        })

    # Handicap prices are not derived from the goal model here. Include them
    # only when the provider supplies a complete, normalizable market.
    for opt in parsed["handicap"]:
        estimate = get_probability(opt)
        if not estimate:
            continue
        prob, prob_source = estimate
        evaluated_picks.append({
            "market_type": "Handicap",
            "selection": opt["selection"],
            "model_probability": round(prob, 4),
            "fair_odds": round(1.0 / max(prob, 0.01), 2),
            "available_odds": opt["odds"],
            "expected_value": round((prob * opt["odds"]) - 1.0, 4),
            "confidence_tier": "Market implied",
            "ai_rationale": generate_ai_rationale(home, away, "Handicap", opt["selection"], prob, pred, "market"),
            "event_id": eid,
            "market_id": opt["market_id"],
            "outcome_id": opt["outcome_id"],
            "specifier": opt["specifier"],
            "probability_source": prob_source,
        })

    # Pick THE ONE SINGLE DEFINITIVE SUREST PREDICTION
    high_conviction = [
        p for p in evaluated_picks
        if p["model_probability"] >= 0.65 and p["available_odds"] >= 1.12
    ]
    if high_conviction:
        high_conviction.sort(key=lambda x: (x["model_probability"], x["expected_value"]), reverse=True)
        surest_pick = high_conviction[0]
    elif evaluated_picks:
        evaluated_picks.sort(key=lambda x: x["model_probability"], reverse=True)
        surest_pick = evaluated_picks[0]
    else:
        surest_pick = None

    # Identify THE ONE BEST PROP (Corners, Cards, or complementary market)
    prop_candidates = [
        p for p in evaluated_picks
        if (p["market_type"] in ["Corners", "Cards & Bookings"] or (
            surest_pick and p["market_type"] != surest_pick["market_type"] and p["model_probability"] >= 0.60
        )) and (not surest_pick or p["selection"] != surest_pick["selection"])
    ]
    prop_candidates.sort(
        key=lambda x: (x["market_type"] in ["Corners", "Cards & Bookings"], x["model_probability"]),
        reverse=True
    )
    best_prop = prop_candidates[0] if prop_candidates else None

    numeric_id = abs(zlib.crc32(eid.encode("utf-8"))) % 1000000 + 100000

    return {
        "id": numeric_id,
        "fixture": f"{home} vs {away}",
        "home_team": home,
        "away_team": away,
        "league": league_name,
        "league_code": sporty_league_code(league_name),
        "kickoff": kickoff_dt.isoformat(),
        "status": "scheduled",
        "ft_home_goals": None,
        "ft_away_goals": None,
        "surest_prediction": {
            "market": surest_pick["market_type"],
            "selection": surest_pick["selection"],
            "prob": surest_pick["model_probability"],
            "odds": surest_pick["available_odds"],
            "fair_odds": surest_pick["fair_odds"],
            "ev": surest_pick["expected_value"],
            "probability_source": surest_pick.get("probability_source", "model"),
            "odds_source": surest_pick.get("odds_source", "bookmaker"),
            "confidence_tier": surest_pick["confidence_tier"],
            "rationale": surest_pick["ai_rationale"],
            "event_id": surest_pick.get("event_id"),
            "market_id": surest_pick.get("market_id"),
            "outcome_id": surest_pick.get("outcome_id"),
            "specifier": surest_pick.get("specifier"),
        } if surest_pick else None,
        "best_prop": {
            "market": best_prop["market_type"],
            "selection": best_prop["selection"],
            "prob": best_prop["model_probability"],
            "odds": best_prop["available_odds"],
            "fair_odds": best_prop["fair_odds"],
            "ev": best_prop["expected_value"],
            "probability_source": best_prop.get("probability_source", "model"),
            "confidence_tier": best_prop["confidence_tier"],
            "rationale": best_prop["ai_rationale"],
            "event_id": best_prop.get("event_id"),
            "market_id": best_prop.get("market_id"),
            "outcome_id": best_prop.get("outcome_id"),
            "specifier": best_prop.get("specifier"),
        } if best_prop else None,
        "top_surest_picks": [
            {
                "market": surest_pick["market_type"],
                "selection": surest_pick["selection"],
                "prob": surest_pick["model_probability"],
                "odds": surest_pick["available_odds"],
                "fair_odds": surest_pick["fair_odds"],
                "odds_source": surest_pick.get("odds_source", "bookmaker"),
                "probability_source": surest_pick.get("probability_source", "model"),
                "ev": surest_pick["expected_value"],
                "confidence_tier": surest_pick["confidence_tier"],
                "rationale": surest_pick["ai_rationale"],
                "event_id": surest_pick.get("event_id"),
                "market_id": surest_pick.get("market_id"),
                "outcome_id": surest_pick.get("outcome_id"),
                "specifier": surest_pick.get("specifier"),
            }
        ] if surest_pick else [],
        "ai_analysis": surest_pick["ai_rationale"] if surest_pick else (
            "No available two-way market price or team-specific model estimate supports a forecast."
        ),
        "expected_goals": exp_goals,
        "markets": [
            {
                "market": p["market_type"],
                "selection": p["selection"],
                "odds": p["available_odds"],
                "probability": p["model_probability"],
                "probability_source": p.get("probability_source", "model"),
                "ev": p["expected_value"],
                "rationale": p.get("ai_rationale"),
                "confidence_tier": p["confidence_tier"],
                "event_id": p.get("event_id"),
                "market_id": p.get("market_id"),
                "outcome_id": p.get("outcome_id"),
                "specifier": p.get("specifier"),
            }
            for p in evaluated_picks
        ],
    }


@router.get("/matches")
async def list_match_predictions(
    league_code: str | None = Query(None),
    status_filter: str | None = Query(None, description="scheduled or finished"),
    limit: int = Query(120, ge=1, le=250),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Returns matches structured for the frontend MatchList component, complete with AI surest picks and outlook."""
    dc = await _get_fitted_model(db)

    match_items: list[dict[str, Any]] = []

    # 1. First, fetch real upcoming games from SportyBet Nigeria
    if status_filter in [None, "scheduled"]:
        try:
            sporty_events = fetch_sporty_upcoming_events()
            for ev in sporty_events[:limit]:
                item = _build_sporty_match_item(ev, dc)
                if item:
                    if league_code and league_code not in {item["league_code"], item["league"]}:
                        continue
                    # This listing is read-only. The daily accumulator flow
                    # persists its selected pre-match picks for result grading.
                    match_items.append(item)
        except Exception as e:
            print(f"Error merging sporty events: {e}")

    # 2. Query database matches
    base_query = (
        select(Match)
        .options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.season).selectinload(Season.league),
            selectinload(Match.odds),
        )
    )

    matches_to_analyze: list[Match] = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if status_filter:
        if status_filter == "scheduled":
            stmt = base_query.where(Match.status == "scheduled", Match.kickoff >= now).order_by(asc(Match.kickoff)).limit(limit)
        else:
            stmt = base_query.where(Match.status == "finished").order_by(desc(Match.kickoff)).limit(limit)
        res = await db.execute(stmt)
        matches_to_analyze = list(res.scalars().all())
    else:
        live_stmt = base_query.where(Match.status == "in_play").order_by(asc(Match.kickoff))
        live_res = await db.execute(live_stmt)
        live_matches = list(live_res.scalars().all())

        sched_stmt = base_query.where(Match.status == "scheduled", Match.kickoff >= now).order_by(asc(Match.kickoff)).limit(limit - 20)
        sched_res = await db.execute(sched_stmt)
        scheduled_matches = list(sched_res.scalars().all())

        fin_stmt = base_query.where(Match.status == "finished").order_by(desc(Match.kickoff)).limit(20)
        fin_res = await db.execute(fin_stmt)
        finished_matches = list(fin_res.scalars().all())

        matches_to_analyze = live_matches + scheduled_matches + finished_matches

    if league_code:
        matches_to_analyze = [
            match for match in matches_to_analyze
            if match.season and match.season.league and match.season.league.code == league_code
        ]

    for m in matches_to_analyze:
        try:
            pred = dc.predict_match(m.home_team.name, m.away_team.name)
        except Exception:
            continue

        p_1x2 = pred.get("1x2", {})
        p_dc = pred.get("double_chance", {})
        p_dnb = pred.get("draw_no_bet", {})
        p_totals = pred.get("totals", {})
        p_team_totals = pred.get("team_totals", {})
        p_btts = pred.get("btts", {})
        p_cs = pred.get("clean_sheets", {})
        p_hc = pred.get("handicaps", {})

        odds_by_sel: dict[str, float] = {}
        for o in m.odds:
            odds_by_sel[f"{o.market_type}_{o.selection}"] = o.odds

        # Candidate markets spanning 1X2, DC, DNB, GG/NG, Game O/U, Team O/U, Clean Sheet, Handicaps, Corners, Cards
        all_candidates = [
            # 1X2
            ("1X2", f"{m.home_team.name} to Win", p_1x2.get("home", 0.0), "1x2_home"),
            ("1X2", "Draw", p_1x2.get("draw", 0.0), "1x2_draw"),
            ("1X2", f"{m.away_team.name} to Win", p_1x2.get("away", 0.0), "1x2_away"),

            # Double Chance
            ("Double Chance", f"{m.home_team.name} or Draw (1X)", p_dc.get("1x", 0.0), "dc_1x"),
            ("Double Chance", f"Draw or {m.away_team.name} (X2)", p_dc.get("x2", 0.0), "dc_x2"),
            ("Double Chance", f"{m.home_team.name} or {m.away_team.name} (12)", p_dc.get("12", 0.0), "dc_12"),

            # Draw No Bet
            ("Draw No Bet", f"{m.home_team.name} (DNB)", p_dnb.get("home", 0.0), "dnb_home"),
            ("Draw No Bet", f"{m.away_team.name} (DNB)", p_dnb.get("away", 0.0), "dnb_away"),

            # Both Teams to Score (GG / NG)
            ("GG / NG", "GG (Both Teams Score - Yes)", p_btts.get("yes", 0.0), "btts_yes"),
            ("GG / NG", "NG (Both Teams Score - No)", p_btts.get("no", 0.0), "btts_no"),

            # Match Goals
            ("Match Goals", "Over 0.5 Goals", p_totals.get("over_under_0.5", {}).get("over", 0.0), "ou_0.5_over"),
            ("Match Goals", "Over 1.5 Goals", p_totals.get("over_under_1.5", {}).get("over", 0.0), "ou_1.5_over"),
            ("Match Goals", "Under 1.5 Goals", p_totals.get("over_under_1.5", {}).get("under", 0.0), "ou_1.5_under"),
            ("Match Goals", "Over 2.5 Goals", p_totals.get("over_under_2.5", {}).get("over", 0.0), "over_under_2.5_over"),
            ("Match Goals", "Under 2.5 Goals", p_totals.get("over_under_2.5", {}).get("under", 0.0), "over_under_2.5_under"),
            ("Match Goals", "Over 3.5 Goals", p_totals.get("over_under_3.5", {}).get("over", 0.0), "ou_3.5_over"),
            ("Match Goals", "Under 3.5 Goals", p_totals.get("over_under_3.5", {}).get("under", 0.0), "ou_3.5_under"),

            # Team Goals (Home & Away)
            ("Team Goals", f"{m.home_team.name} Over 0.5 Goals", p_team_totals.get("home_over_under_0.5", {}).get("over", 0.0), "home_ou_0.5_over"),
            ("Team Goals", f"{m.home_team.name} Over 1.5 Goals", p_team_totals.get("home_over_under_1.5", {}).get("over", 0.0), "home_ou_1.5_over"),
            ("Team Goals", f"{m.away_team.name} Over 0.5 Goals", p_team_totals.get("away_over_under_0.5", {}).get("over", 0.0), "away_ou_0.5_over"),
            ("Team Goals", f"{m.away_team.name} Over 1.5 Goals", p_team_totals.get("away_over_under_1.5", {}).get("over", 0.0), "away_ou_1.5_over"),

            # Clean Sheets
            ("Clean Sheet", f"{m.home_team.name} Clean Sheet (Yes)", p_cs.get("home_clean_sheet_yes", 0.0), "cs_home_yes"),
            ("Clean Sheet", f"{m.away_team.name} Clean Sheet (Yes)", p_cs.get("away_clean_sheet_yes", 0.0), "cs_away_yes"),

            # Handicaps
            ("Handicap", f"{m.home_team.name} (+1.5 Handicap)", p_hc.get("asian_handicap_home_+1.5", 0.0), "hc_home_plus1.5"),
            ("Handicap", f"{m.away_team.name} (+1.5 Handicap)", p_hc.get("asian_handicap_away_+1.5", 0.0), "hc_away_plus1.5"),
            ("Handicap", f"{m.home_team.name} (-1.5 Handicap)", p_hc.get("asian_handicap_home_-1.5", 0.0), "hc_home_minus1.5"),
            ("Handicap", f"{m.away_team.name} (-1.5 Handicap)", p_hc.get("asian_handicap_away_-1.5", 0.0), "hc_away_minus1.5"),

        ]

        evaluated_picks: list[dict[str, Any]] = []
        for m_type, sel, prob, odds_key in all_candidates:
            if prob < 0.20:
                continue

            raw_odds = odds_by_sel.get(odds_key)
            fair_odds = MarketEngine.calculate_fair_odds(prob)
            available_odds = raw_odds if (raw_odds and raw_odds > 1.0) else fair_odds
            ev = MarketEngine.calculate_expected_value(prob, raw_odds) if raw_odds and raw_odds > 1.0 else None
            conf = classifier.evaluate(prob, raw_odds, quality_score=1.0) if raw_odds and raw_odds > 1.0 else None

            evaluated_picks.append({
                "market_type": m_type,
                "selection": sel,
                "model_probability": round(prob, 4),
                "fair_odds": fair_odds,
                "available_odds": available_odds,
                "expected_value": ev,
                "odds_source": "bookmaker" if raw_odds and raw_odds > 1.0 else "model_fair",
                "confidence_tier": conf.tier if conf else "Model forecast ? odds unavailable",
                "is_value": ev is not None and ev >= 0.0,
                "ai_rationale": generate_ai_rationale(m.home_team.name, m.away_team.name, m_type, sel, prob, pred),
            })

        # Rank all picks by conviction (probability)
        sorted_picks = sorted(evaluated_picks, key=lambda x: x["model_probability"], reverse=True)
        surest_pick = sorted_picks[0] if sorted_picks else None

        # Identify THE ONE BEST PROP (Corners, Cards, or complementary market)
        prop_candidates = [
            p for p in evaluated_picks
            if (p["market_type"] in ["Corners", "Cards & Bookings"] or (
                surest_pick and p["market_type"] != surest_pick["market_type"] and p["model_probability"] >= 0.60
            )) and (not surest_pick or p["selection"] != surest_pick["selection"])
        ]
        prop_candidates.sort(
            key=lambda x: (x["market_type"] in ["Corners", "Cards & Bookings"], x["model_probability"]),
            reverse=True
        )
        best_prop = prop_candidates[0] if prop_candidates else None

        # Extract Top 4 Non-Conflicting Surest Picks for this game
        top_surest: list[dict[str, Any]] = []
        seen_markets: set[str] = set()
        for p in sorted_picks:
            if p["market_type"] not in seen_markets and p["model_probability"] >= 0.55:
                top_surest.append(p)
                seen_markets.add(p["market_type"])
            if len(top_surest) >= 4:
                break
        if not top_surest and sorted_picks:
            top_surest = sorted_picks[:3]

        match_items.append({
            "id": m.id,
            "fixture": f"{m.home_team.name} vs {m.away_team.name}",
            "home_team": m.home_team.name,
            "away_team": m.away_team.name,
            "league": m.season.league.name if m.season and m.season.league else "European League",
            "league_code": m.season.league.code if m.season and m.season.league else "",
            "kickoff": m.kickoff.isoformat(),
            "status": m.status,
            "ft_home_goals": m.ft_home_goals,
            "ft_away_goals": m.ft_away_goals,
            "surest_prediction": {
                "market": surest_pick["market_type"],
                "selection": surest_pick["selection"],
                "prob": surest_pick["model_probability"],
                "odds": surest_pick["available_odds"],
                "fair_odds": surest_pick["fair_odds"],
                "odds_source": surest_pick.get("odds_source", "bookmaker"),
                "ev": surest_pick["expected_value"],
                "confidence_tier": surest_pick["confidence_tier"],
                "rationale": surest_pick["ai_rationale"],
                "event_id": surest_pick.get("event_id"),
                "market_id": surest_pick.get("market_id"),
                "outcome_id": surest_pick.get("outcome_id"),
                "specifier": surest_pick.get("specifier"),
            } if surest_pick else None,
            "best_prop": {
                "market": best_prop["market_type"],
                "selection": best_prop["selection"],
                "prob": best_prop["model_probability"],
                "odds": best_prop["available_odds"],
                "fair_odds": best_prop["fair_odds"],
                "odds_source": best_prop.get("odds_source", "bookmaker"),
                "probability_source": best_prop.get("probability_source", "model"),
                "ev": best_prop["expected_value"],
                "confidence_tier": best_prop["confidence_tier"],
                "rationale": best_prop["ai_rationale"],
                "event_id": best_prop.get("event_id"),
                "market_id": best_prop.get("market_id"),
                "outcome_id": best_prop.get("outcome_id"),
                "specifier": best_prop.get("specifier"),
            } if best_prop else None,
            "top_surest_picks": [
                {
                    "market": surest_pick["market_type"],
                    "selection": surest_pick["selection"],
                    "prob": surest_pick["model_probability"],
                    "odds": surest_pick["available_odds"],
                    "odds_source": surest_pick.get("odds_source", "bookmaker"),
                    "fair_odds": surest_pick["fair_odds"],
                    "ev": surest_pick["expected_value"],
                    "confidence_tier": surest_pick["confidence_tier"],
                    "rationale": surest_pick["ai_rationale"],
                    "event_id": surest_pick.get("event_id"),
                    "market_id": surest_pick.get("market_id"),
                    "outcome_id": surest_pick.get("outcome_id"),
                    "specifier": surest_pick.get("specifier"),
                }
            ] if surest_pick else [],
            "ai_analysis": surest_pick["ai_rationale"] if surest_pick else (
                f"Statistical Poisson simulation projects {pred.get('expected_goals', {}).get('total', 2.5)} total xG."
            ),
            "expected_goals": pred.get("expected_goals"),
            "markets": [
                {
                    "market": p["market_type"],
                    "selection": p["selection"],
                    "odds": p["available_odds"],
                    "probability": p["model_probability"],
                    "ev": p["expected_value"],
                    "confidence_tier": p["confidence_tier"],
                    "event_id": p.get("event_id"),
                    "market_id": p.get("market_id"),
                    "outcome_id": p.get("outcome_id"),
                    "specifier": p.get("specifier"),
                }
                for p in evaluated_picks
            ],
        })

    # The live feed is the source of current fixtures; merge local fixtures while
    # avoiding duplicates and return one chronological list across both sources.
    seen: set[tuple[str, str, str]] = set()
    unique_items: list[dict[str, Any]] = []
    for item in match_items:
        kickoff = datetime.fromisoformat(item["kickoff"].replace("Z", "+00:00"))
        day = kickoff.astimezone(timezone.utc).date().isoformat() if kickoff.tzinfo else kickoff.date().isoformat()
        key = (item["home_team"].casefold().strip(), item["away_team"].casefold().strip(), day)
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
    unique_items.sort(key=lambda item: datetime.fromisoformat(item["kickoff"].replace("Z", "+00:00")).timestamp())
    return unique_items[:limit]


@router.get("")
async def list_predictions(
    match_id: int | None = Query(None, description="Filter for a specific match ID"),
    league_code: str | None = Query(None),
    status_filter: str | None = Query(None, description="scheduled or finished"),
    min_prob: float = Query(0.30, description="Minimum model probability"),
    limit: int = Query(60, ge=1, le=150),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Generates probabilistic predictions on upcoming and current fixtures with AI surest picks."""
    dc = await _get_fitted_model(db)
    if not dc:
        return []

    target_stmt = (
        select(Match)
        .options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.season).selectinload(Season.league),
            selectinload(Match.odds),
        )
    )

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if match_id:
        target_stmt = target_stmt.where(Match.id == match_id)
    elif status_filter:
        if status_filter == "scheduled":
            target_stmt = target_stmt.where(Match.status == "scheduled", Match.kickoff >= now).order_by(asc(Match.kickoff))
        else:
            target_stmt = target_stmt.where(Match.status == "finished").order_by(desc(Match.kickoff))
    else:
        target_stmt = target_stmt.where(Match.status == "scheduled", Match.kickoff >= now).order_by(asc(Match.kickoff))

    target_stmt = target_stmt.limit(limit)
    res = await db.execute(target_stmt)
    matches_to_predict = res.scalars().all()

    model_version = await db.scalar(
        select(ModelVersion).where(ModelVersion.model_name == "Dixon-Coles", ModelVersion.version == "live-1")
    )
    if not model_version:
        model_version = ModelVersion(
            model_name="Dixon-Coles",
            version="live-1",
            status="experimental",
            hyperparameters={"xi": dc.xi, "max_goals": dc.max_goals},
            training_samples=getattr(dc, "training_sample_count", None),
            trained_at=datetime.now(timezone.utc),
        )
        db.add(model_version)
        await db.flush()
    else:
        model_version.trained_at = datetime.now(timezone.utc)
        model_version.training_samples = getattr(dc, "training_sample_count", None)

    results: list[dict[str, Any]] = []

    for m in matches_to_predict:
        if m.home_team.name not in dc.team_idx or m.away_team.name not in dc.team_idx:
            continue
        try:
            pred = dc.predict_match(m.home_team.name, m.away_team.name)
        except Exception:
            continue

        p_1x2 = pred.get("1x2", {})
        p_dc = pred.get("double_chance", {})
        p_dnb = pred.get("draw_no_bet", {})
        p_totals = pred.get("totals", {})
        p_team_totals = pred.get("team_totals", {})
        p_btts = pred.get("btts", {})
        p_cs = pred.get("clean_sheets", {})
        p_hc = pred.get("handicaps", {})
        p_corners = pred.get("corners", {})
        p_cards = pred.get("cards", {})

        odds_by_sel: dict[str, float] = {}
        for o in m.odds:
            odds_by_sel[f"{o.market_type}_{o.selection}"] = o.odds

        all_candidates = [
            ("1X2", f"{m.home_team.name} to Win", p_1x2.get("home", 0.0), "1x2_home"),
            ("1X2", "Draw", p_1x2.get("draw", 0.0), "1x2_draw"),
            ("1X2", f"{m.away_team.name} to Win", p_1x2.get("away", 0.0), "1x2_away"),
            ("Double Chance", f"{m.home_team.name} or Draw (1X)", p_dc.get("1x", 0.0), "dc_1x"),
            ("Double Chance", f"Draw or {m.away_team.name} (X2)", p_dc.get("x2", 0.0), "dc_x2"),
            ("Double Chance", f"{m.home_team.name} or {m.away_team.name} (12)", p_dc.get("12", 0.0), "dc_12"),
            ("GG / NG", "GG (Both Teams Score - Yes)", p_btts.get("yes", 0.0), "btts_yes"),
            ("GG / NG", "NG (Both Teams Score - No)", p_btts.get("no", 0.0), "btts_no"),
            ("Match Goals", "Over 1.5 Goals", p_totals.get("over_under_1.5", {}).get("over", 0.0), "ou_1.5_over"),
            ("Match Goals", "Under 1.5 Goals", p_totals.get("over_under_1.5", {}).get("under", 0.0), "ou_1.5_under"),
            ("Match Goals", "Over 2.5 Goals", p_totals.get("over_under_2.5", {}).get("over", 0.0), "over_under_2.5_over"),
            ("Match Goals", "Under 2.5 Goals", p_totals.get("over_under_2.5", {}).get("under", 0.0), "over_under_2.5_under"),
            ("Team Goals", f"{m.home_team.name} Over 0.5 Goals", p_team_totals.get("home_over_under_0.5", {}).get("over", 0.0), "home_ou_0.5_over"),
            ("Team Goals", f"{m.away_team.name} Over 0.5 Goals", p_team_totals.get("away_over_under_0.5", {}).get("over", 0.0), "away_ou_0.5_over"),
        ]

        evaluated_picks: list[dict[str, Any]] = []

        for m_type, sel, prob, odds_key in all_candidates:
            if prob < min_prob:
                continue

            raw_odds = odds_by_sel.get(odds_key)
            fair_odds = MarketEngine.calculate_fair_odds(prob)
            available_odds = raw_odds if (raw_odds and raw_odds > 1.0) else None

            ev = MarketEngine.calculate_expected_value(prob, available_odds) if available_odds else None
            conf = classifier.evaluate(prob, available_odds, quality_score=1.0) if available_odds else None

            saved_prediction = await db.scalar(
                select(Prediction).where(
                    Prediction.match_id == m.id,
                    Prediction.model_version_id == model_version.id,
                    Prediction.market_type == m_type,
                    Prediction.selection == sel,
                    Prediction.settled.is_(False),
                )
            )
            if saved_prediction is None:
                db.add(Prediction(
                    match_id=m.id,
                    model_version_id=model_version.id,
                    market_type=m_type,
                    selection=sel,
                    probability=prob,
                    fair_odds=fair_odds,
                    available_odds=available_odds,
                    expected_value=ev,
                    confidence_tier=conf.tier if conf else "Model Forecast",
                    model_output={"expected_goals": pred.get("expected_goals")},
                    outcome="pending",
                    settled=False,
                ))
            # Keep the first pre-match forecast immutable for honest result analysis.

            evaluated_picks.append({
                "match_id": m.id,
                "fixture": f"{m.home_team.name} vs {m.away_team.name}",
                "home_team": m.home_team.name,
                "away_team": m.away_team.name,
                "league": m.season.league.name if m.season and m.season.league else "",
                "kickoff": m.kickoff.isoformat(),
                "status": m.status,
                "market_type": m_type,
                "selection": sel,
                "model_probability": round(prob, 4),
                "fair_odds": fair_odds,
                "available_odds": available_odds,
                "expected_value": ev,
                "confidence_tier": conf.tier if conf else "Model forecast ? odds unavailable",
                "odds_source": "bookmaker" if available_odds else "unavailable",
                "is_value": ev is not None and ev >= 0.0,
                "ai_rationale": generate_ai_rationale(m.home_team.name, m.away_team.name, m_type, sel, prob, pred),
                "expected_goals": pred.get("expected_goals"),
            })

        if evaluated_picks:
            evaluated_picks.sort(key=lambda x: x["model_probability"], reverse=True)
            surest_pick = evaluated_picks[0]

            for item in evaluated_picks:
                item["is_surest_pick"] = (item == surest_pick)
                results.append(item)

    return results
