from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any
from sqlalchemy import JSON, Boolean, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.match import Match


class League(Base):
    """Competition / League entity."""

    __tablename__ = "leagues"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    tier: Mapped[str] = mapped_column(String(10), default="A", nullable=False)  # "A" or "B"
    data_coverage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    seasons: Mapped[list[Season]] = relationship(
        "Season", back_populates="league", cascade="all, delete-orphan"
    )


class Season(Base):
    """Season within a league."""

    __tablename__ = "seasons"

    league_id: Mapped[int] = mapped_column(
        ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False, index=True
    )
    season_code: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "2425", "2024"
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("league_id", "season_code", name="uq_league_season"),
    )

    league: Mapped[League] = relationship("League", back_populates="seasons")
    matches: Mapped[list[Match]] = relationship("Match", back_populates="season")
