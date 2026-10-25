from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from pathlib import Path
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from backend.config import settings
from backend.db.base import Base

# Ensure data directory exists if using local sqlite
if "sqlite" in settings.database_url:
    data_dir = settings.base_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

# SQLAlchemy Async Engine configuration
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=(settings.environment == "development" and settings.log_level == "DEBUG"),
    future=True,
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection helper for FastAPI routes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    # Import all models to ensure they are registered with Base metadata
    import backend.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
