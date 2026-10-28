from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.engine import get_db
from backend.services.prediction_audit import build_prediction_audit

router = APIRouter(prefix="/audit", tags=["Audit & Post-Match Review"])


@router.get("/recent")
async def get_recent_audit(
    date: str | None = Query(None, description="Audit date string YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Grades saved predictions against completed match scores."""
    result = await build_prediction_audit(db, date)
    return result
