from __future__ import annotations

import pytest
import httpx
from backend.main import app


@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "football-prediction-engine" in data["service"]


@pytest.mark.asyncio
async def test_performance_summary_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/performance/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "operational"
        assert "dataset_statistics" in data
        assert data["dataset_statistics"]["total_matches"] > 0


@pytest.mark.asyncio
async def test_fixtures_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/fixtures?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        first = data[0]
        assert "home_team" in first
        assert "away_team" in first
        assert "kickoff" in first


@pytest.mark.asyncio
async def test_accumulators_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/accumulators?category=solid_core")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
