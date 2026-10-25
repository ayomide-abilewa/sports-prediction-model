from __future__ import annotations

from datetime import datetime, timezone
from backend.telegram.formatters import TelegramFormatter


def test_format_wat_time():
    # 14:00 UTC = 15:00 WAT
    dt_utc = datetime(2026, 10, 25, 14, 0, 0, tzinfo=timezone.utc)
    wat_str = TelegramFormatter.format_wat_time(dt_utc)
    assert "15:00 WAT" in wat_str


def test_format_single_prediction():
    pred = {
        "fixture": "Liverpool vs Arsenal",
        "league": "Premier League",
        "kickoff": "2026-10-25T16:30:00+00:00",
        "market_type": "1x2",
        "selection": "home",
        "model_probability": 0.58,
        "fair_odds": 1.72,
        "available_odds": 1.95,
        "expected_value": 0.131,
        "confidence_tier": "Tier 3 – Sharp Value",
    }
    msg = TelegramFormatter.format_single_prediction(pred)
    assert "Liverpool vs Arsenal" in msg
    assert "1X2" in msg
    assert "58.0%" in msg
    assert "+13.1%" in msg
    assert "Tier 3 – Sharp Value" in msg


def test_format_accumulator_slip():
    slip = {
        "slip_name": "Product 1: Banker Rollover",
        "combined_odds": 2.25,
        "joint_probability": 0.51,
        "expected_return": 0.147,
        "risk_class": "Low Risk",
        "legs": [
            {"fixture": "Man City vs Everton", "market": "1x2", "selection": "home", "odds": 1.30, "probability": 0.82},
            {"fixture": "Real Madrid vs Osasuna", "market": "1x2", "selection": "home", "odds": 1.73, "probability": 0.62},
        ],
    }
    msg = TelegramFormatter.format_accumulator_slip(slip, booking_code="SPORTY-12345")
    assert "BANKER ROLLOVER" in msg
    assert "2.25" in msg
    assert "SPORTY-12345" in msg
