from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.engine import get_db
from backend.models.league import League
from backend.models.match import Match
from backend.models.odds import MarketOdds
from backend.models.team import Team
from backend.services.audit_service import build_audit_report

router = APIRouter(prefix="/performance", tags=["Performance"])


@router.get("/audit")
async def get_performance_audit() -> dict[str, Any]:
    """Returns the comprehensive recent picks audit grading recent fixtures."""
    return build_audit_report()


@router.get("/summary")
async def get_performance_summary(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Returns database metrics, match coverage, and historical prediction stats."""
    # Count totals
    total_matches = await db.scalar(select(func.count(Match.id)))
    finished_matches = await db.scalar(
        select(func.count(Match.id)).where(Match.status == "finished")
    )
    total_teams = await db.scalar(select(func.count(Team.id)))
    total_leagues = await db.scalar(select(func.count(League.id)))
    total_odds = await db.scalar(select(func.count(MarketOdds.id)))

    return {
        "status": "operational",
        "dataset_statistics": {
            "total_matches": total_matches or 0,
            "finished_matches": finished_matches or 0,
            "total_teams": total_teams or 0,
            "active_leagues": total_leagues or 0,
            "total_odds_records": total_odds or 0,
        },
        "model_benchmarks": {
            "dixon_coles": {
                "status": "active",
                "calibration_brier_target": 0.20,
                "home_advantage_baseline": "+0.25 log-goals",
                "time_decay_xi": 0.005,
            },
            "elo_ratings": {
                "status": "active",
                "k_factor": 20.0,
                "home_advantage": 100.0,
            },
        },
    }
