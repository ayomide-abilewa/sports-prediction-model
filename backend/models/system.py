from __future__ import annotations

from datetime import datetime
from typing import Any
from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from backend.db.base import Base


class DataSourceLog(Base):
    """Execution log for data ingestion pipelines."""

    __tablename__ = "data_source_logs"

    source_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # success, partial, failed

    records_processed: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True)
    records_new: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True)
    records_updated: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )


class SystemAuditLog(Base):
    """Audit log for sensitive actions (admin overrides, model deployments)."""

    __tablename__ = "system_audit_logs"

    actor: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
