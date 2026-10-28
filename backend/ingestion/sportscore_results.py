from __future__ import annotations

import asyncio
import logging
import time
from datetime import date
from typing import Any

import httpx

logger = logging.getLogger(__name__)
_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_CACHE_TTL_SECONDS = 300


def _fetch_finished_results(day: str, competition: str | None = None) -> list[dict[str, Any]]:
    cache_key = f"{day}:{competition or '*'}"
    cached = _CACHE.get(cache_key)
    now = time.monotonic()
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    try:
        response = httpx.get(
            "https://sportscore.com/api/v1/fixtures/",
            params={
                "sport": "football", "date": day, "status": "finished", "limit": 200,
                **({"competition": competition} if competition else {}),
            },
            headers={"User-Agent": "FootballProbAnalytics/1.0"},
            timeout=12.0,
        )
        response.raise_for_status()
        payload = response.json()
        matches = payload.get("matches", [])
        if isinstance(matches, list):
            results = [m for m in matches if isinstance(m, dict)]
            _CACHE[cache_key] = (now, results)
            return results
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.warning("sportscore_results_fetch_failed", extra={"date": day, "error": str(exc)})
    return []


async def fetch_finished_results(day: date, competition: str | None = None) -> list[dict[str, Any]]:
    """Read the public daily football results feed without blocking the API loop."""
    return await asyncio.to_thread(_fetch_finished_results, day.isoformat(), competition)
