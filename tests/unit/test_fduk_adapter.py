from __future__ import annotations

from datetime import datetime
from backend.ingestion.football_data_uk import FootballDataUKAdapter


def test_build_csv_url():
    adapter = FootballDataUKAdapter()

    # Premier League 2024/25
    url = adapter.build_csv_url("ENG-Premier League", "2425")
    assert "mmz4281/2425/E0.csv" in url

    # La Liga 2023/24
    url = adapter.build_csv_url("ESP-La Liga", "2324")
    assert "mmz4281/2324/SP1.csv" in url

    # Serie A with full year string e.g. "2024"
    url = adapter.build_csv_url("ITA-Serie A", "2024")
    assert "mmz4281/2425/I1.csv" in url


def test_parse_kickoff_datetime():
    adapter = FootballDataUKAdapter()

    # DD/MM/YYYY with Time
    dt = adapter.parse_kickoff_datetime("17/08/2024", "12:30")
    assert dt.year == 2024
    assert dt.month == 8
    assert dt.day == 17
    assert dt.hour == 12
    assert dt.minute == 30

    # DD/MM/YY without Time
    dt = adapter.parse_kickoff_datetime("18/08/24")
    assert dt.year == 2024
    assert dt.month == 8
    assert dt.day == 18
    assert dt.hour == 15  # Default hour
