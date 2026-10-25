from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any
from sqlalchemy import JSON, Boolean, Date, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.match import Lineup, Match, MatchStatistics, PlayerMatchStats


class Team(Base):
    """Football Club / Team entity."""

    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    country: Mapped[str] = mapped_column(String(50), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    current_elo: Mapped[float] = mapped_column(Float, default=1500.0, nullable=False)

    home_matches: Mapped[list[Match]] = relationship(
        "Match", foreign_keys="Match.home_team_id", back_populates="home_team"
    )
    away_matches: Mapped[list[Match]] = relationship(
        "Match", foreign_keys="Match.away_team_id", back_populates="away_team"
    )
    players: Mapped[list[Player]] = relationship("Player", back_populates="current_team")
    match_stats: Mapped[list[MatchStatistics]] = relationship(
        "MatchStatistics", back_populates="team"
    )


class Player(Base):
    """Player entity."""

    __tablename__ = "players"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    current_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True
    )
    position: Mapped[str | None] = mapped_column(String(30), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    current_team: Mapped[Team | None] = relationship("Team", back_populates="players")
    match_stats: Mapped[list[PlayerMatchStats]] = relationship(
        "PlayerMatchStats", back_populates="player"
    )


class Manager(Base):
    """Team Manager / Head Coach."""

    __tablename__ = "managers"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    current_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True
    )
    appointed_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class Referee(Base):
    """Match Referee."""

    __tablename__ = "referees"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    country: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    avg_yellows_per_match: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_reds_per_match: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_fouls_per_match: Mapped[float | None] = mapped_column(Float, nullable=True)

    matches: Mapped[list[Match]] = relationship("Match", back_populates="referee")
