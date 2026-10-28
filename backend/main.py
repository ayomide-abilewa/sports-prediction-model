from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from backend.api import accumulators, audit, fixtures, in_play, matches, performance, predictions
from backend.config import settings
from backend.db.init_db import seed_initial_data
from backend.ingestion.sportybet_service import start_sporty_background_sync
from backend.ingestion.scheduler import IngestionScheduler
from backend.ingestion.football_data_uk import FootballDataUKAdapter

logger = structlog.get_logger()


async def _refresh_results_periodically() -> None:
    adapter = FootballDataUKAdapter()
    scheduler = IngestionScheduler()
    while True:
        now = datetime.now(timezone.utc)
        season_start = now.year if now.month >= 7 else now.year - 1
        season_code = f"{season_start % 100:02d}{(season_start + 1) % 100:02d}"
        for league_code in adapter.LEAGUE_MAP:
            try:
                result = await scheduler.ingest_league_season(league_code, season_code)
                if result.errors:
                    logger.warning("scheduled_results_refresh_partial", league=league_code, errors=result.errors)
            except Exception as exc:
                logger.warning("scheduled_results_refresh_failed", league=league_code, error=str(exc))
        await asyncio.sleep(6 * 60 * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown procedures."""
    logger.info("server_startup", environment=settings.environment)
    # Ensure database tables and initial league/bookmaker references are seeded
    try:
        await seed_initial_data()
    except Exception as exc:
        logger.warning("db_init_warning", error=str(exc))
    # Start periodic background synchronization for SportyBet live and upcoming odds
    try:
        await start_sporty_background_sync()
    except Exception as exc:
        logger.warning("sporty_background_sync_warning", error=str(exc))
    asyncio.create_task(_refresh_results_periodically())
    yield
    logger.info("server_shutdown")


app = FastAPI(
    title="Advanced AI Football Probability Engine",
    description="Probabilistic football prediction engine, quantitative market analytics, and accumulator combinator.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Middleware for Next.js frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(fixtures.router, prefix="/api/v1")
app.include_router(matches.router, prefix="/api/v1")
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(accumulators.router, prefix="/api/v1")
app.include_router(performance.router, prefix="/api/v1")
app.include_router(in_play.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "football-prediction-engine",
        "environment": settings.environment,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.api_host, port=settings.api_port, reload=True)
