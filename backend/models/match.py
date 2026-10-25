from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.league import Season
    from backend.models.odds import MarketOdds
    from backend.models.prediction import Prediction
    from backend.models.team import Player, Referee, Team


class Match(Base):
    """Fixture and Match Results."""

    __tablename__ = "matches"

    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    home_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    away_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    referee_id: Mapped[int | None] = mapped_column(
        ForeignKey("referees.id", ondelete="SET NULL"), nullable=True, index=True
    )

    kickoff: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="scheduled", nullable=False, index=True
    )  # scheduled, in_play, finished, postponed, cancelled

    # Scorelines
    ft_home_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ft_away_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ht_home_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ht_away_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)

    source: Mapped[str] = mapped_column(String(50), default="football_data_uk", nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("season_id", "home_team_id", "away_team_id", "kickoff", name="uq_match_fixture"),
        Index("ix_matches_kickoff_status", "kickoff", "status"),
    )

    season: Mapped[Season] = relationship("Season", back_populates="matches")
    home_team: Mapped[Team] = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team: Mapped[Team] = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    referee: Mapped[Referee | None] = relationship("Referee", back_populates="matches")

    statistics: Mapped[list[MatchStatistics]] = relationship("MatchStatistics", back_populates="match", cascade="all, delete-orphan")
    player_stats: Mapped[list[PlayerMatchStats]] = relationship("PlayerMatchStats", back_populates="match", cascade="all, delete-orphan")
    lineups: Mapped[list[Lineup]] = relationship("Lineup", back_populates="match", cascade="all, delete-orphan")
    odds: Mapped[list[MarketOdds]] = relationship("MarketOdds", back_populates="match", cascade="all, delete-orphan")
    predictions: Mapped[list[Prediction]] = relationship("Prediction", back_populates="match", cascade="all, delete-orphan")


class MatchStatistics(Base):
    """Team-level match statistics (shots, xG, cards, corners, etc.)."""

    __tablename__ = "match_statistics"

    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_home: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Advanced metrics
    xg: Mapped[float | None] = mapped_column(Float, nullable=True)
    npxg: Mapped[float | None] = mapped_column(Float, nullable=True)
    xga: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Traditional metrics
    shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shots_inside_box: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shots_outside_box: Mapped[int | None] = mapped_column(Integer, nullable=True)
    possession: Mapped[float | None] = mapped_column(Float, nullable=True)
    pass_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Tactical & event counts
    progressive_passes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deep_completions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crosses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tackles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interceptions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clearances: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blocks: Mapped[int | None] = mapped_column(Integer, nullable=True)

    corners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    yellow_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    red_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fouls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    big_chances: Mapped[int | None] = mapped_column(Integer, nullable=True)

    source: Mapped[str] = mapped_column(String(50), default="football_data_uk", nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("match_id", "team_id", name="uq_match_team_stats"),
    )

    match: Mapped[Match] = relationship("Match", back_populates="statistics")
    team: Mapped[Team] = relationship("Team", back_populates="match_stats")


class PlayerMatchStats(Base):
    """Player performance metrics within a match."""

    __tablename__ = "player_match_stats"

    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )

    starter: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    goals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assists: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xg: Mapped[float | None] = mapped_column(Float, nullable=True)
    xa: Mapped[float | None] = mapped_column(Float, nullable=True)
    shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="fbref", nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    match: Mapped[Match] = relationship("Match", back_populates="player_stats")
    player: Mapped[Player] = relationship("Player", back_populates="match_stats")


class Lineup(Base):
    """Match lineup snapshot (expected or confirmed)."""

    __tablename__ = "lineups"

    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )

    players: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    formation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="predicted", nullable=False
    )  # "predicted", "confirmed"
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    match: Mapped[Match] = relationship("Match", back_populates="lineups")
