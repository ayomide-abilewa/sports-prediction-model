from __future__ import annotations

import os
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/football_predictions.db"
    database_url_sync: str = "sqlite:///./data/football_predictions.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Telegram
    telegram_bot_token: str = ""
    telegram_channel_id: str = ""

    # SportyBet
    sportybet_enabled: bool = False

    # API & Frontend URLs (for Telegram Bot and Remote Deployments)
    api_base_url: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    webapp_url: str = os.getenv("TELEGRAM_WEBAPP_URL", "")

    # App
    secret_key: str = "dev-secret-key-super-secure-change-in-prod-12345"
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Data collection
    fduk_base_url: str = "https://www.football-data.co.uk"
    scrape_delay_seconds: int = 3

    # Model parameters
    min_ev_threshold: float = 0.025
    dixon_coles_xi: float = 0.005
    default_elo: float = 1500.0
    elo_k_factor: float = 20.0
    elo_home_advantage: float = 100.0

    # Base directory
    base_dir: Path = Path(__file__).resolve().parent.parent


settings = Settings()
