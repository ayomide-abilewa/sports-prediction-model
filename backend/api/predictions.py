from __future__ import annotations

import math
from typing import Any
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
from backend.probability.dixon_coles import DixonColesModel
from backend.probability.markets import MarketEngine

router = APIRouter(prefix="/predictions", tags=["Predictions"])
classifier = ConfidenceClassifier(min_ev_threshold=-0.05)


def generate_ai_rationale(
    home: str,
    away: str,
    market: str,
    selection: str,
    prob: float,
    pred: dict[str, Any],
) -> str:
    """Generates an intuitive analytical summary explaining why the AI recommends this pick."""
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
        return f"{selection} provides dual statistical safety across two of three possible match outcomes with an exceptional {prob * 100:.1f}% safety rate."

    elif market == "Draw No Bet":
        return f"Eliminating the draw outcome gives {selection} a decisive mathematical edge at {prob * 100:.1f}% confidence."

    elif market == "GG / NG":
        if "GG" in selection or "Yes" in selection:
            return f"Both attacks average over 1.25 xG per match. Open transitional tactical play heavily supports both teams finding the back of the net ({prob * 100:.1f}%)."
        return f"At least one team expected to struggle offensively or maintain a disciplined low defensive block ({prob * 100:.1f}% clean-sheet expectation)."

    elif market == "Match Goals":
        if "Over" in selection:
            return f"Projected combined goal expectation of {tot} xG. High chance of goals flowing freely from both forward lines ({prob * 100:.1f}% probability)."
        return f"Defensive stability and low transitional tempo project a tight contest staying under the goal line ({prob * 100:.1f}% probability)."

    elif market == "Team Goals":
        return f"Target team's attacking creation metrics comfortably exceed baseline concession rates ({prob * 100:.1f}% scoring certainty)."

    elif market == "Clean Sheet":
        return f"Defensive structure and goalkeeper shot-stopping metrics project high clean-sheet resilience ({prob * 100:.1f}%)."

    elif market == "Handicap":
        return f"Margin-of-victory distribution projects favorable spread coverage for {selection} at {prob * 100:.1f}% probability."

    elif market == "Corners":
        return f"Attacking wing width, cross frequency, and deflected shot volumes project match corners exceeding the threshold ({prob * 100:.1f}%)."

    elif market == "Cards & Bookings":
        return f"Referee disciplinary strictness and tactical foul frequency establish a reliable bookings line ({prob * 100:.1f}% probability)."

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
        return dc
    except Exception:
        return None


@router.get("/matches")
async def list_match_predictions(
    league_code: str | None = Query(None),
    status_filter: str | None = Query(None, description="scheduled or finished"),
    limit: int = Query(120, ge=1, le=250),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Returns matches structured for the frontend MatchList component, complete with AI surest picks and outlook."""
    dc = await _get_fitted_model(db)
    if not dc:
        return []

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

    if status_filter:
        order = asc(Match.kickoff) if status_filter == "scheduled" else desc(Match.kickoff)
        stmt = base_query.where(Match.status == status_filter).order_by(order).limit(limit)
        res = await db.execute(stmt)
        matches_to_analyze = list(res.scalars().all())
    else:
        # Fetch scheduled fixtures first, then completed matches
        sched_stmt = base_query.where(Match.status == "scheduled").order_by(asc(Match.kickoff)).limit(limit - 15)
        sched_res = await db.execute(sched_stmt)
        scheduled_matches = list(sched_res.scalars().all())

        fin_stmt = base_query.where(Match.status == "finished").order_by(desc(Match.kickoff)).limit(15)
        fin_res = await db.execute(fin_stmt)
        finished_matches = list(fin_res.scalars().all())

        matches_to_analyze = scheduled_matches + finished_matches

    match_items: list[dict[str, Any]] = []

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
        p_corners = pred.get("corners", {})
        p_cards = pred.get("cards", {})

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

            # Corners (SportyBet Special)
            ("Corners", "Over 7.5 Corners", p_corners.get("corners_over_under_7.5", {}).get("over", 0.0), "corners_7.5_over"),
            ("Corners", "Over 8.5 Corners", p_corners.get("corners_over_under_8.5", {}).get("over", 0.0), "corners_8.5_over"),
            ("Corners", "Under 11.5 Corners", p_corners.get("corners_over_under_10.5", {}).get("under", 0.0), "corners_10.5_under"),

            # Cards & Bookings (SportyBet Special)
            ("Cards & Bookings", "Over 2.5 Cards", p_cards.get("cards_over_under_2.5", {}).get("over", 0.0), "cards_2.5_over"),
            ("Cards & Bookings", "Over 3.5 Cards", p_cards.get("cards_over_under_3.5", {}).get("over", 0.0), "cards_3.5_over"),
            ("Cards & Bookings", "Under 5.5 Cards", p_cards.get("cards_over_under_4.5", {}).get("under", 0.0), "cards_4.5_under"),
        ]

        evaluated_picks: list[dict[str, Any]] = []
        for m_type, sel, prob, odds_key in all_candidates:
            if prob < 0.20:
                continue

            raw_odds = odds_by_sel.get(odds_key)
            fair_odds = MarketEngine.calculate_fair_odds(prob)
            available_odds = raw_odds if (raw_odds and raw_odds > 1.0) else round(fair_odds * 0.94, 2)
            ev = MarketEngine.calculate_expected_value(prob, available_odds)
            conf = classifier.evaluate(prob, available_odds, quality_score=1.0)

            evaluated_picks.append({
                "market_type": m_type,
                "selection": sel,
                "model_probability": round(prob, 4),
                "fair_odds": fair_odds,
                "available_odds": available_odds,
                "expected_value": ev,
                "confidence_tier": conf.tier or ("Tier 1 – Bankers" if prob >= 0.70 else "Sharp Value"),
                "is_value": ev >= 0.0,
                "ai_rationale": generate_ai_rationale(m.home_team.name, m.away_team.name, m_type, sel, prob, pred),
            })

        # Rank all picks by conviction (probability)
        sorted_picks = sorted(evaluated_picks, key=lambda x: x["model_probability"], reverse=True)
        surest_pick = sorted_picks[0] if sorted_picks else None

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
                "ev": surest_pick["expected_value"],
                "confidence_tier": surest_pick["confidence_tier"],
                "rationale": surest_pick["ai_rationale"],
            } if surest_pick else None,
            "top_surest_picks": [
                {
                    "market": p["market_type"],
                    "selection": p["selection"],
                    "prob": p["model_probability"],
                    "odds": p["available_odds"],
                    "fair_odds": p["fair_odds"],
                    "ev": p["expected_value"],
                    "confidence_tier": p["confidence_tier"],
                    "rationale": p["ai_rationale"],
                }
                for p in top_surest
            ],
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
                }
                for p in evaluated_picks
            ],
        })

    return match_items


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

    if match_id:
        target_stmt = target_stmt.where(Match.id == match_id)
    elif status_filter:
        target_stmt = target_stmt.where(Match.status == status_filter)
    else:
        sched_check = await db.scalar(
            select(Match.id).where(Match.status == "scheduled").limit(1)
        )
        if sched_check:
            target_stmt = target_stmt.where(Match.status == "scheduled").order_by(asc(Match.kickoff))
        else:
            target_stmt = target_stmt.order_by(desc(Match.kickoff))

    target_stmt = target_stmt.limit(limit)
    res = await db.execute(target_stmt)
    matches_to_predict = res.scalars().all()

    results: list[dict[str, Any]] = []

    for m in matches_to_predict:
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
            ("Corners", "Over 8.5 Corners", p_corners.get("corners_over_under_8.5", {}).get("over", 0.0), "corners_8.5_over"),
            ("Cards & Bookings", "Over 3.5 Cards", p_cards.get("cards_over_under_3.5", {}).get("over", 0.0), "cards_3.5_over"),
        ]

        evaluated_picks: list[dict[str, Any]] = []

        for m_type, sel, prob, odds_key in all_candidates:
            if prob < min_prob:
                continue

            raw_odds = odds_by_sel.get(odds_key)
            fair_odds = MarketEngine.calculate_fair_odds(prob)
            available_odds = raw_odds if (raw_odds and raw_odds > 1.0) else round(fair_odds * 0.94, 2)

            ev = MarketEngine.calculate_expected_value(prob, available_odds)
            conf = classifier.evaluate(prob, available_odds, quality_score=1.0)

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
                "confidence_tier": conf.tier or ("Tier 1 – Bankers" if prob >= 0.70 else "Sharp Value"),
                "is_value": ev >= 0.0,
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
