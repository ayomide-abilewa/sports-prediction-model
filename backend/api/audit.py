from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Query

from backend.services.audit_service import build_audit_report

router = APIRouter(prefix="/audit", tags=["Audit & Post-Match Review"])


@router.get("/recent")
async def get_recent_audit(
    date: str = Query("2026-10-25", description="Audit date string YYYY-MM-DD")
) -> dict[str, Any]:
    """Returns the comprehensive recent picks audit grading recent Domestic & UEFA completed fixtures."""
    return build_audit_report(date)
