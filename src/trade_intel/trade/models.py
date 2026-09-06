from __future__ import annotations

from dataclasses import dataclass

from trade_intel.provenance import Provenance


@dataclass(frozen=True)
class CountryCode:
    code: int
    iso3: str
    name: str
    role: str
    entry_expired_date: str | None
    provenance: Provenance


@dataclass(frozen=True)
class ProductCodeCandidate:
    hs_code: str
    description: str
    parent: str | None
    is_leaf: bool
    aggregation_level: int
    standard_unit: str | None
    provenance: Provenance


@dataclass(frozen=True)
class TradeFlow:
    importer_code: str
    importer_name: str
    importer_comtrade_code: int
    exporter_code: str | None
    exporter_name: str
    exporter_comtrade_code: int
    hs_code: str
    product_description: str | None
    year: int
    flow: str
    trade_value_usd: float
    source: str
    source_query_metadata: dict[str, str | int | float | bool | None]
    provenance: Provenance
