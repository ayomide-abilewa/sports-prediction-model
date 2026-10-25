from __future__ import annotations

import pytest
from backend.ingestion.team_mapper import TeamMapper


def test_team_mapper_exact_aliases():
    mapper = TeamMapper()

    # Exact alias matches
    assert mapper.resolve("Man United")[0] == "Manchester United"
    assert mapper.resolve("Man Utd")[0] == "Manchester United"
    assert mapper.resolve("MUFC")[0] == "Manchester United"
    assert mapper.resolve("Spurs")[0] == "Tottenham"
    assert mapper.resolve("PSG")[0] == "Paris Saint-Germain"
    assert mapper.resolve("FC Barcelona")[0] == "Barcelona"
    assert mapper.resolve("Bayern München")[0] == "Bayern Munich"
    assert mapper.resolve("Atleti")[0] == "Atletico Madrid"


def test_team_mapper_fuzzy_matching():
    mapper = TeamMapper(min_confidence=80.0)

    # Minor typos / variations
    canonical, score = mapper.resolve("Wolverhampton")
    assert canonical == "Wolves"
    assert score >= 80.0

    canonical, score = mapper.resolve("Brighton and Hove")
    assert canonical == "Brighton"
    assert score >= 80.0


def test_team_mapper_normalization():
    mapper = TeamMapper()
    # Check diacritics removal
    assert mapper.normalize_string("Atlético Madrid") == "atletico madrid"
    assert mapper.normalize_string("München") == "munchen"
    assert mapper.normalize_string("Nott'm Forest") == "nott m forest"


def test_team_mapper_unresolved_fallback():
    mapper = TeamMapper(min_confidence=90.0)
    # A completely unknown name with no resemblance should fall back cleanly
    raw = "Random Unknown FC 123"
    canonical, score = mapper.resolve(raw)
    assert canonical == raw
    assert score < 90.0
