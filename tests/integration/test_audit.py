import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.services.audit_service import build_audit_report


@pytest.mark.asyncio
async def test_audit_recent_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/audit/recent")
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "fixtures" in data
        assert len(data["fixtures"]) == 21
        assert data["summary"]["main_picks"]["wins"] == 14
        assert data["summary"]["main_picks"]["losses"] == 7
        assert data["summary"]["main_picks"]["win_rate"] == 66.7
        assert data["summary"]["main_picks"]["net_profit"] == 1.91
        assert data["summary"]["main_picks"]["roi"] == 9.1
        assert data["summary"]["best_props"]["wins"] == 15
        assert data["summary"]["best_props"]["losses"] == 4
        assert data["summary"]["best_props"]["win_rate"] == 78.9
        assert data["summary"]["brier_calibration"] == 0.1897


@pytest.mark.asyncio
async def test_performance_audit_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/performance/audit")
        assert response.status_code == 200
        data = response.json()
        assert "formatted_text" in data
        assert "Inter vs Fiorentina" in data["formatted_text"]
