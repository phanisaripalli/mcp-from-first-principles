from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Provenance:
    """Enough source metadata for a reader to inspect where data came from."""

    source: str
    endpoint: str
    query_params: dict[str, str]
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    page: int | None = None
    pages: int | None = None
    per_page: int | None = None
    total: int | None = None
    notes: str | None = None

    @classmethod
    def from_worldbank(
        cls,
        *,
        endpoint: str,
        query_params: dict[str, str],
        metadata: dict[str, Any] | None = None,
        notes: str | None = None,
    ) -> "Provenance":
        metadata = metadata or {}
        return cls(
            source="World Bank Indicators API",
            endpoint=endpoint,
            query_params=dict(query_params),
            page=_optional_int(metadata.get("page")),
            pages=_optional_int(metadata.get("pages")),
            per_page=_optional_int(metadata.get("per_page")),
            total=_optional_int(metadata.get("total")),
            notes=notes,
        )


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)

