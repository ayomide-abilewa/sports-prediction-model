from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.prediction import Prediction


class GeneratedSlip(Base):
    """Accumulator / Combination Bet Slip."""

    __tablename__ = "generated_slips"

    slip_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # banker_rollover, solid_core, sharp_multi, high_yield, corners_cards

    combined_odds: Mapped[float] = mapped_column(Float, nullable=False)
    joint_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_class: Mapped[str | None] = mapped_column(String(30), nullable=True)
    booking_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    status: Mapped[str] = mapped_column(
        String(30), default="generated", nullable=False, index=True
    )  # generated, published, settled, won, lost

    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    legs: Mapped[list[SlipLeg]] = relationship("SlipLeg", back_populates="slip", cascade="all, delete-orphan")
    booking_codes: Mapped[list[BookingCode]] = relationship("BookingCode", back_populates="slip", cascade="all, delete-orphan")


class SlipLeg(Base):
    """Individual leg within an accumulator slip."""

    __tablename__ = "slip_legs"

    slip_id: Mapped[int] = mapped_column(
        ForeignKey("generated_slips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prediction_id: Mapped[int] = mapped_column(
        ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )

    selection: Mapped[str] = mapped_column(String(50), nullable=False)
    odds: Mapped[float] = mapped_column(Float, nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    ev: Mapped[float | None] = mapped_column(Float, nullable=True)
    leg_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    outcome: Mapped[str | None] = mapped_column(
        String(20), default="pending", nullable=True
    )  # pending, won, lost, void

    slip: Mapped[GeneratedSlip] = relationship("GeneratedSlip", back_populates="legs")
    prediction: Mapped[Prediction] = relationship("Prediction", back_populates="slip_legs")


class BookingCode(Base):
    """Bookmaker booking code reference."""

    __tablename__ = "booking_codes"

    slip_id: Mapped[int] = mapped_column(
        ForeignKey("generated_slips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bookmaker: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "SportyBet"
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    slip: Mapped[GeneratedSlip] = relationship("GeneratedSlip", back_populates="booking_codes")
