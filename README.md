# Advanced AI Football Probability Engine & Betting Analytics Platform

[![GitHub Repo](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/ayomide-abilewa/sports-prediction-model)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-brightgreen.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-teal.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14.2%2B-black.svg)](https://nextjs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-quality, research-driven football probabilistic prediction ecosystem combining statistical modelling, automated historical ingestion, value betting analytics, correlation-aware accumulator generation, and real-time Telegram bot alerts.

---

## Architecture Overview

```
                                      ┌────────────────────────┐
                                      │ Football-Data.co.uk    │
                                      │ CSV Ingestion Engine   │
                                      └───────────┬────────────┘
                                                  │
                                                  ▼
┌────────────────────────┐            ┌────────────────────────┐
│  Next.js Analytics     │◄───────────┤  FastAPI REST Backend  │
│  Terminal Dashboard    │            │  (SQLAlchemy 2.0 Async)│
└────────────────────────┘            └───────────┬────────────┘
                                                  │
                                                  ▼
┌────────────────────────┐            ┌────────────────────────┐
│  Telegram Bot          │◄───────────┤   Probability Engine   │
│  (Live Polling / Push) │            │  (Dixon-Coles Bivariate│
└────────────────────────┘            │   Poisson, Elo, NBinom)│
                                      └────────────────────────┘
```

---

## Core Features

- **Pillar 1: Data Infrastructure**: Automated historical ingestion across 11 European leagues with team canonical resolution (`RapidFuzz`) and multi-attribute data completeness validation. Seeded with 1,140+ real matches and bookmaker odds (Pinnacle, Bet365).
- **Pillar 2: Advanced Probability Engine**:
  - **Vectorized Dixon-Coles Bivariate Poisson**: Time-decay weighting ($w(t) = \exp(-\xi t)$), low-score correction $\tau(x, y; \rho)$, and joint scoreline probability matrices summing strictly to $1.0$.
  - **Dynamic Elo System**: With home advantage (+100 points) and logarithmic margin-of-victory scaling.
  - **Negative Binomial Models**: Dedicated overdispersed models for Corner totals (6.5 to 11.5) and Card bookings (2.5 to 5.5).
  - **Lineup Impact Intelligence**: Pre-lineup squad core ratings vs confirmed XI deviation tracking.
- **Pillar 3: Model Validation & Calibration**: Isotonic Regression and Platt scaling, Brier score, log-loss, and Closing Line Value (CLV) benchmarks.
- **Pillar 4: Value Engine & Accumulator Combinator**:
  - **4-Tier Confidence Classification**: Bankers (75-92%), Solid Core (60-75%), Sharp Value (45-60%), High Yield (28-45%).
  - **Correlation Engine**: Multi-selection conflict elimination and intra-match correlation adjustments.
  - **5 Blueprint Slip Recipes**: Banker Rollover (2.0x-2.5x), Solid Core Multiplier (5.0x-7.0x), Sharp Multi-League (12x-20x), Weekend High-Yield (40x-100x+), Corners & Cards.
  - **Quantitative Bankroll Engine**: Conservative Fractional Kelly (Quarter-Kelly default) with $5\%$ single-exposure caps.
- **Pillar 5: Telegram Bot Service**: Responds to `/today`, `/bankers`, `/2_odds`, `/5_odds`, `/15_odds`, `/high_yield`, `/performance`, and formats timestamps in West Africa Time (WAT).
- **Pillar 6: Next.js Terminal Dashboard**: Dark terminal aesthetic with live metrics, fixtures explorer, interactive accumulator generator, and model calibration registry.

---

## Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone https://github.com/ayomide-abilewa/sports-prediction-model.git
cd sports-prediction-model

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # Windows PowerShell
source .venv/bin/activate       # Linux/Mac

# Install backend dependencies
pip install -e ".[dev]"
```

### 2. Database Initialization & Seeding

```bash
# Initialize SQLite database and seed base reference leagues/bookmakers
python -m backend.db.init_db

# Seed real historical match data and betting odds (EPL, La Liga, Serie A)
python scripts/seed_historical.py --leagues "ENG-Premier League" "ESP-La Liga" "ITA-Serie A" --seasons "2425"
```

### 3. Run the Automated Test Suite

```bash
pytest tests -v
# 40 passed in ~6.5s
```

### 4. Start the FastAPI Backend Server

```bash
uvicorn backend.main:app --reload
# API available at: http://localhost:8000
# Interactive Swagger Documentation: http://localhost:8000/docs
```

---

## Connecting Your Telegram Bot

You can connect your Telegram bot in under 60 seconds:

1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Send `/newbot`, name your bot (e.g. `MyFootballOddsBot`), and copy the provided API Token.
3. Start the bot polling service:

```bash
python scripts/run_telegram_bot.py --token <YOUR_TELEGRAM_BOT_TOKEN>
```

Or add it to your `.env` file:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
```
and simply run:
```bash
python scripts/run_telegram_bot.py
```

Now open Telegram, message your bot, and try:
- `/start` or `/help`
- `/today`
- `/predictions`
- `/bankers`
- `/2_odds`
- `/5_odds`
- `/15_odds`
- `/high_yield`
- `/performance`

---

## Starting the Web Dashboard (Next.js)

```bash
cd frontend
npm install
npm run dev
# Dashboard available at: http://localhost:3000
```

---

## License

MIT License. Designed and built for quantitative football research and probabilistic sports modelling.
