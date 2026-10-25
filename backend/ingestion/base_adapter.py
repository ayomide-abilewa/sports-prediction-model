from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import structlog

logger = structlog.get_logger()


@dataclass
class IngestionResult:
    """Result container for a data ingestion operation."""

    source: str
    operation: str
    status: str = "pending"  # "success", "partial", "failed"
    records_processed: int = 0
    records_new: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    @property
    def duration_seconds(self) -> float | None:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def complete(self, status: str | None = None) -> None:
        self.completed_at = datetime.utcnow()
        if status:
            self.status = status
        elif self.errors:
            self.status = "partial" if self.records_new > 0 or self.records_updated > 0 else "failed"
        else:
            self.status = "success"


class BaseAdapter(ABC):
    """Abstract base class for all football data adapters.
    
    Guarantees consistent data extraction, normalization, and error isolation.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier for this data provider."""
        ...

    @abstractmethod
    async def fetch_matches(self, league_code: str, season: str) -> list[dict[str, Any]]:
        """Fetch match results and basic stats for a competition and season."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the data source endpoint is accessible."""
        ...
