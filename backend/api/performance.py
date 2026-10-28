from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.engine import get_db
from backend.models.league import League
from backend.models.match import Match
from backend.models.odds import MarketOdds
from backend.models.prediction import ModelVersion, Prediction
from backend.models.team import Team
from backend.services.prediction_audit import build_prediction_audit

router = APIRouter(prefix="/performance", tags=["Performance"])


@router.get("/audit")
async def get_performance_audit(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Returns results for saved predictions that have a final score."""
    result = await build_prediction_audit(db)
    return result


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
    total_odds = await db.scalar(select(func.count(MarketOdds.id)))
    active_leagues = await db.scalar(select(func.count(League.id)).where(League.active.is_(True)))
    prediction_count = await db.scalar(select(func.count(Prediction.id)))
    settled_prediction_count = await db.scalar(
        select(func.count(Prediction.id)).where(Prediction.settled.is_(True))
    )
    model_versions = (await db.execute(select(ModelVersion).order_by(ModelVersion.trained_at.desc()))).scalars().all()

    return {
        "status": "operational",
        "dataset_statistics": {
            "total_matches": total_matches or 0,
            "finished_matches": finished_matches or 0,
            "total_teams": total_teams or 0,
            "active_leagues": active_leagues or 0,
            "total_odds_records": total_odds or 0,
            "saved_predictions": prediction_count or 0,
            "settled_predictions": settled_prediction_count or 0,
        },
        "model_versions": [
            {
                "name": model.model_name,
                "version": model.version,
                "status": model.status,
                "trained_at": model.trained_at.isoformat() if model.trained_at else None,
                "training_samples": model.training_samples,
                "brier_score": model.brier_score,
                "log_loss": model.log_loss,
                "clv_rate": model.clv_rate,
            }
            for model in model_versions
        ],
    }
