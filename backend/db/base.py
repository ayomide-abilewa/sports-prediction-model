from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """Declarative base class for all SQLAlchemy ORM models."""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        # Convert CamelCase to snake_case table name
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        if not name.endswith("s"):
            name = f"{name}s"
        return name

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=datetime.utcnow,
        nullable=False,
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance attributes to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
