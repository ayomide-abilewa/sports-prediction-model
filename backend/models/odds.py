from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.match import Match


class Bookmaker(Base):
    """Bookmaker / Sportsbook entity."""

    __tablename__ = "bookmakers"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    odds: Mapped[list[MarketOdds]] = relationship("MarketOdds", back_populates="bookmaker")


class MarketOdds(Base):
    """Historical or current market odds."""

    __tablename__ = "market_odds"

    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bookmaker_id: Mapped[int] = mapped_column(
        ForeignKey("bookmakers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    market_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # e.g., "1x2", "over_under_2.5", "btts", "corners_9.5"
    selection: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g., "home", "draw", "away", "over", "under", "yes", "no"
    odds: Mapped[float] = mapped_column(Float, nullable=False)
    implied_prob: Mapped[float | None] = mapped_column(Float, nullable=True)

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    is_opening: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_closing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("ix_odds_match_market", "match_id", "market_type", "selection"),
    )

    match: Mapped[Match] = relationship("Match", back_populates="odds")
    bookmaker: Mapped[Bookmaker] = relationship("Bookmaker", back_populates="odds")
