from __future__ import annotations

from datetime import datetime
from typing import Any
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.base import Base


class TelegramSubscriber(Base):
    """Telegram Bot Subscriber / Channel."""

    __tablename__ = "telegram_subscribers"

    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    subscribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    notifications: Mapped[list[NotificationLog]] = relationship(
        "NotificationLog", back_populates="subscriber", cascade="all, delete-orphan"
    )


class NotificationLog(Base):
    """Log of all sent notifications."""

    __tablename__ = "notification_logs"

    subscriber_id: Mapped[int | None] = mapped_column(
        ForeignKey("telegram_subscribers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    notification_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # daily_summary, new_prediction, lineup_alert, result_update
    content_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="sent", nullable=False
    )  # sent, failed, skipped
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )

    subscriber: Mapped[TelegramSubscriber | None] = relationship(
        "TelegramSubscriber", back_populates="notifications"
    )
