from __future__ import annotations

from dataclasses import dataclass

from trade_intel.provenance import Provenance


@dataclass(frozen=True)
class IndicatorSummary:
    code: str
    name: str
    unit: str | None
    source_id: str
    source_name: str
    source_note: str | None
    source_organization: str | None
    topics: tuple[str, ...]
    provenance: Provenance


@dataclass(frozen=True)
class IndicatorObservation:
    country_code: str
    country_name: str
    indicator_code: str
    indicator_name: str
    year: int
    value: float | None
    unit: str | None
    source: str
    source_note: str | None
    provenance: Provenance


@dataclass(frozen=True)
class CountryProfile:
    country_code: str
    iso2_code: str
    name: str
    region_code: str
    region_name: str
    income_level_code: str
    income_level_name: str
    lending_type_code: str
    lending_type_name: str
    capital_city: str | None
    longitude: float | None
    latitude: float | None
    provenance: Provenance

