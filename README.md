# Advanced AI Football Probability Engine

A production-quality, research-driven football probability prediction system combining statistical modelling, machine learning, and automated betting analytics.

## Architecture

- **Backend**: Python 3.12+ / FastAPI / SQLAlchemy 2.0 / Alembic
- **Models**: Dixon-Coles / xG / CatBoost / XGBoost / Negative Binomial
- **Frontend**: Next.js / React / TypeScript / Tailwind CSS
- **Automation**: Telegram Bot / SportyBet integration
- **Data**: Football-Data.co.uk / FBref / Understat

## Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Copy environment file
copy .env.example .env  # Windows
cp .env.example .env  # Linux/Mac

# 4. Initialize database
python -m backend.db.init

# 5. Seed historical data
python scripts/seed_historical.py

# 6. Run the API server
uvicorn backend.main:app --reload

# 7. Run tests
pytest tests/ -v
```

## Project Structure

```
backend/           # Python backend (FastAPI + ML models)
  ingestion/       # Data collection adapters
  features/        # Feature engineering
  probability/     # Probability models
  validation/      # Model validation & backtesting
  betting/         # Value engine & accumulator builder
  telegram/        # Telegram bot
  api/             # REST API routes
  models/          # Database ORM models
  db/              # Database engine & sessions
frontend/          # Next.js web dashboard
tests/             # Test suite
scripts/           # Utility scripts
notebooks/         # Research notebooks
docs/              # Documentation
```

## Development Phases

1. ✅ Foundation & Data Infrastructure
2. 🔲 Core Goals Models
3. 🔲 Lineup & Non-Goal Models
4. 🔲 Value Engine & Accumulator Builder
5. 🔲 Telegram & SportyBet
6. 🔲 Web Dashboard
7. 🔲 Testing & Production

## License

MIT
