from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.match import Match
    from backend.models.slip import SlipLeg


class ModelVersion(Base):
    """Model metadata, hyperparameter tracking, and production status."""

    __tablename__ = "model_versions"

    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="experimental", nullable=False, index=True
    )  # experimental, validated, production, retired

    hyperparameters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    brier_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    log_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    clv_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    training_samples: Mapped[int | None] = mapped_column(Integer, nullable=True)
    training_cutoff: Mapped[date | None] = mapped_column(Date, nullable=True)
    artifact_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    predictions: Mapped[list[Prediction]] = relationship("Prediction", back_populates="model_version")
    backtest_runs: Mapped[list[BacktestRun]] = relationship("BacktestRun", back_populates="model_version")


class Prediction(Base):
    """Individual market prediction output."""

    __tablename__ = "predictions"

    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_version_id: Mapped[int] = mapped_column(
        ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    market_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    selection: Mapped[str] = mapped_column(String(50), nullable=False)

    probability: Mapped[float] = mapped_column(Float, nullable=False)
    calibrated_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    fair_odds: Mapped[float | None] = mapped_column(Float, nullable=True)
    available_odds: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_tier: Mapped[str | None] = mapped_column(String(30), nullable=True)

    data_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    outcome: Mapped[str | None] = mapped_column(
        String(20), default="pending", nullable=True
    )  # pending, won, lost, void, push
    settled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_predictions_match_market", "match_id", "market_type", "selection"),
    )

    match: Mapped[Match] = relationship("Match", back_populates="predictions")
    model_version: Mapped[ModelVersion] = relationship("ModelVersion", back_populates="predictions")
    features: Mapped[list[PredictionFeature]] = relationship("PredictionFeature", back_populates="prediction", cascade="all, delete-orphan")
    slip_legs: Mapped[list[SlipLeg]] = relationship("SlipLeg", back_populates="prediction")


class PredictionFeature(Base):
    """Features and SHAP values used to generate a prediction (for explainability)."""

    __tablename__ = "prediction_features"

    prediction_id: Mapped[int] = mapped_column(
        ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False)
    feature_value: Mapped[float] = mapped_column(Float, nullable=False)
    shap_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    prediction: Mapped[Prediction] = relationship("Prediction", back_populates="features")


class BacktestRun(Base):
    """Walk-forward backtest execution log and metrics."""

    __tablename__ = "backtest_runs"

    model_version_id: Mapped[int] = mapped_column(
        ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    train_start: Mapped[date] = mapped_column(Date, nullable=False)
    train_end: Mapped[date] = mapped_column(Date, nullable=False)
    test_start: Mapped[date] = mapped_column(Date, nullable=False)
    test_end: Mapped[date] = mapped_column(Date, nullable=False)

    num_predictions: Mapped[int] = mapped_column(Integer, nullable=False)
    brier_score: Mapped[float] = mapped_column(Float, nullable=False)
    log_loss: Mapped[float] = mapped_column(Float, nullable=False)
    calibration_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    clv_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    roi: Mapped[float | None] = mapped_column(Float, nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    model_version: Mapped[ModelVersion] = relationship("ModelVersion", back_populates="backtest_runs")
