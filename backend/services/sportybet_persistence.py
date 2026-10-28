from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import zlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.league import League, Season
from backend.models.match import Match
from backend.models.odds import Bookmaker, MarketOdds
from backend.models.prediction import ModelVersion, Prediction
from backend.models.team import Team


def sporty_league_code(league_name: str) -> str:
    return f"SB-{zlib.crc32(league_name.casefold().encode('utf-8')) % 1_000_000:06d}"


async def clear_sporty_fixture_carry(db: AsyncSession, event: dict[str, Any]) -> None:
    """Remove the current-slip marker when a fixture is no longer selected."""
    event_id = str(event.get("eventId") or "")
    if not event_id:
        return
    match = await db.scalar(select(Match).where(Match.source == f"sportybet:{event_id}"))
    if match is None:
        return
    predictions = (await db.execute(
        select(Prediction).where(Prediction.match_id == match.id, Prediction.settled.is_(False))
    )).scalars().all()
    for prediction in predictions:
        output = dict(prediction.model_output or {})
        if output.get("carried"):
            output["carried"] = False
            prediction.model_output = output


async def save_sporty_fixture(db: AsyncSession, event: dict[str, Any], item: dict[str, Any]) -> int:
    """Persist the live event, its current prices, and the exact forecast inputs for later grading."""
    event_id = str(event["eventId"])
    source = f"sportybet:{event_id}"
    kickoff = datetime.fromisoformat(item["kickoff"].replace("Z", "+00:00"))
    kickoff = kickoff.astimezone(timezone.utc).replace(tzinfo=None)
    league_name = item["league"][:100]
    league_code = sporty_league_code(league_name)

    league = await db.scalar(select(League).where(League.code == league_code))
    if league is None:
        league = League(
            name=league_name,
            country="International",
            code=league_code,
            tier="C",
            data_coverage={"fixtures": True, "odds": True, "source": "SportyBet"},
            active=True,
        )
        db.add(league)
        await db.flush()

    year = kickoff.year if kickoff.month >= 7 else kickoff.year - 1
    season_code = f"{year % 100:02d}{(year + 1) % 100:02d}"
    season = await db.scalar(
        select(Season).where(Season.league_id == league.id, Season.season_code == season_code)
    )
    if season is None:
        season = Season(league_id=league.id, season_code=season_code, is_current=True)
        db.add(season)
        await db.flush()

    async def get_team(name: str) -> Team:
        team = await db.scalar(select(Team).where(Team.canonical_name == name))
        if team is None:
            team = Team(name=name, canonical_name=name, country="International", aliases=[name], current_elo=1500.0)
            db.add(team)
            await db.flush()
        return team

    home = await get_team(item["home_team"])
    away = await get_team(item["away_team"])
    match = await db.scalar(select(Match).where(Match.source == source))
    if match is None:
        match = Match(
            season_id=season.id,
            home_team_id=home.id,
            away_team_id=away.id,
            kickoff=kickoff,
            status="scheduled",
            source=source,
        )
        db.add(match)
        await db.flush()
    else:
        match.season_id = season.id
        match.home_team_id = home.id
        match.away_team_id = away.id
        match.kickoff = kickoff
        if match.status not in {"finished", "cancelled"}:
            match.status = "scheduled"

    bookmaker = await db.scalar(select(Bookmaker).where(Bookmaker.code == "SPORTYBET"))
    if bookmaker is None:
        bookmaker = Bookmaker(name="SportyBet", code="SPORTYBET", active=True)
        db.add(bookmaker)
        await db.flush()

    model_version = await db.scalar(
        select(ModelVersion).where(
            ModelVersion.model_name == "Football Forecast",
            ModelVersion.version == "live-feed-v1",
        )
    )
    if model_version is None:
        model_version = ModelVersion(
            model_name="Football Forecast",
            version="live-feed-v1",
            status="experimental",
            hyperparameters={"model": "Dixon-Coles with market fallback"},
            training_samples=0,
            trained_at=datetime.now(timezone.utc),
        )
        db.add(model_version)
        await db.flush()

    # A daily accumulator carries one selection per fixture. Clear the prior
    # carry marker so older, unselected market forecasts are never audited as
    # if they were placed on the slip.
    previous_predictions = (await db.execute(
        select(Prediction).where(
            Prediction.match_id == match.id,
            Prediction.model_version_id == model_version.id,
            Prediction.settled.is_(False),
        )
    )).scalars().all()
    for prediction in previous_predictions:
        output = dict(prediction.model_output or {})
        output["carried"] = False
        prediction.model_output = output

    for market in item.get("markets", []):
        odds = market.get("odds")
        probability = market.get("probability")
        if not odds or odds <= 1.0 or not probability or not 0.0 < probability < 1.0:
            continue
        market_type = str(market.get("market", ""))[:50]
        selection = str(market.get("selection", ""))[:50]
        stored_odds = await db.scalar(
            select(MarketOdds).where(
                MarketOdds.match_id == match.id,
                MarketOdds.bookmaker_id == bookmaker.id,
                MarketOdds.market_type == market_type,
                MarketOdds.selection == selection,
            )
        )
        if stored_odds is None:
            db.add(MarketOdds(
                match_id=match.id,
                bookmaker_id=bookmaker.id,
                market_type=market_type,
                selection=selection,
                odds=odds,
                implied_prob=round(1.0 / odds, 5),
            ))
        else:
            stored_odds.odds = odds
            stored_odds.implied_prob = round(1.0 / odds, 5)

        saved_prediction = await db.scalar(
            select(Prediction).where(
                Prediction.match_id == match.id,
                Prediction.model_version_id == model_version.id,
                Prediction.market_type == market_type,
                Prediction.selection == selection,
                Prediction.settled.is_(False),
            )
        )
        output = {
            "carried": True,
            "probability_source": market.get("probability_source", "market"),
            "event_id": event_id,
            "market_id": market.get("market_id"),
            "outcome_id": market.get("outcome_id"),
            "specifier": market.get("specifier"),
        }
        values = {
            "probability": probability,
            "fair_odds": round(1.0 / probability, 2),
            "available_odds": odds,
            "expected_value": market.get("ev"),
            "confidence_tier": market.get("confidence_tier", "Market implied"),
            "model_output": output,
        }
        if saved_prediction is None:
            db.add(Prediction(
                match_id=match.id,
                model_version_id=model_version.id,
                market_type=market_type,
                selection=selection,
                outcome="pending",
                settled=False,
                **values,
            ))
        else:
            output.update(saved_prediction.model_output or {})
            output["carried"] = True
            saved_prediction.model_output = output
        # Preserve the first forecast snapshot; refreshes update prices but must
        # not rewrite the prediction that will later be scored against results.

    await db.flush()
    return match.id
