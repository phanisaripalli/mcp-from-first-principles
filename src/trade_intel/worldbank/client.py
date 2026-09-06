from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import httpx

from trade_intel.provenance import Provenance
from trade_intel.worldbank.errors import (
    WorldBankAPIError,
    WorldBankHTTPError,
    WorldBankNotFoundError,
    WorldBankResponseError,
)
from trade_intel.worldbank.models import (
    CountryProfile,
    IndicatorObservation,
    IndicatorSummary,
)


class WorldBankClient:
    """Small async client for the World Bank Indicators API V2."""

    def __init__(
        self,
        *,
        base_url: str = "https://api.worldbank.org/v2",
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "WorldBankClient":
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            transport=self._transport,
        )
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def search_indicators(
        self,
        query: str,
        *,
        limit: int = 10,
        max_pages: int = 20,
    ) -> list[IndicatorSummary]:
        clean_query = query.strip().lower()
        if not clean_query:
            raise ValueError("query must not be empty")
        if limit < 1:
            raise ValueError("limit must be at least 1")

        matches: list[IndicatorSummary] = []
        page = 1
        while len(matches) < limit and page <= max_pages:
            metadata, rows, endpoint, params = await self._get_collection(
                "/indicator",
                {"format": "json", "per_page": "100", "page": str(page)},
            )
            for row in rows:
                candidate = _parse_indicator_summary(
                    row,
                    Provenance.from_worldbank(
                        endpoint=endpoint,
                        query_params=params,
                        metadata=metadata,
                        notes=_optional_str(row.get("sourceNote")),
                    ),
                )
                haystack = " ".join(
                    part.lower()
                    for part in (candidate.code, candidate.name, candidate.source_note or "")
                )
                if clean_query in haystack:
                    matches.append(candidate)
                    if len(matches) >= limit:
                        break

            total_pages = int(metadata.get("pages", 1))
            if page >= total_pages:
                break
            page += 1

        return matches

    async def get_indicator(
        self,
        countries: Iterable[str],
        indicator: str,
        start_year: int,
        end_year: int,
    ) -> list[IndicatorObservation]:
        country_codes = [_clean_code(country) for country in countries]
        if not country_codes:
            raise ValueError("countries must contain at least one code")
        if start_year > end_year:
            raise ValueError("start_year must be less than or equal to end_year")

        indicator_code = _clean_indicator_code(indicator)
        indicator_summary = await self._get_indicator_summary(indicator_code)
        metadata, rows, endpoint, params = await self._get_collection(
            f"/country/{';'.join(country_codes)}/indicator/{indicator_code}",
            {
                "format": "json",
                "date": f"{start_year}:{end_year}",
                "per_page": "20000",
            },
        )
        if not rows:
            raise WorldBankNotFoundError(
                f"No observations found for {indicator_code} in {start_year}:{end_year}"
            )

        provenance = Provenance.from_worldbank(
            endpoint=endpoint,
            query_params=params,
            metadata=metadata,
            notes=indicator_summary.source_note,
        )
        return [
            _parse_indicator_observation(row, indicator_summary, provenance)
            for row in rows
        ]

    async def get_country_profile(self, country: str) -> CountryProfile:
        country_code = _clean_code(country)
        metadata, rows, endpoint, params = await self._get_collection(
            f"/country/{country_code}",
            {"format": "json"},
        )
        if not rows:
            raise WorldBankNotFoundError(f"Country not found: {country}")
        return _parse_country_profile(
            rows[0],
            Provenance.from_worldbank(
                endpoint=endpoint,
                query_params=params,
                metadata=metadata,
            ),
        )

    async def _get_indicator_summary(self, indicator_code: str) -> IndicatorSummary:
        metadata, rows, endpoint, params = await self._get_collection(
            f"/indicator/{indicator_code}",
            {"format": "json"},
        )
        if not rows:
            raise WorldBankNotFoundError(f"Indicator not found: {indicator_code}")
        row = rows[0]
        return _parse_indicator_summary(
            row,
            Provenance.from_worldbank(
                endpoint=endpoint,
                query_params=params,
                metadata=metadata,
                notes=_optional_str(row.get("sourceNote")),
            ),
        )

    async def _get_collection(
        self,
        path: str,
        params: dict[str, str],
    ) -> tuple[dict[str, Any], list[dict[str, Any]], str, dict[str, str]]:
        response = await self._request(path, params)
        payload = response.json()
        if _is_worldbank_error(payload):
            message = payload["message"][0]
            raise WorldBankAPIError(
                f"{message.get('key', 'World Bank API error')}: {message.get('value', '')}"
            )
        if not isinstance(payload, list) or len(payload) != 2:
            raise WorldBankResponseError("Expected World Bank collection response")
        metadata, rows = payload
        if not isinstance(metadata, dict) or not isinstance(rows, list):
            raise WorldBankResponseError("Expected metadata and row list")
        if not all(isinstance(row, dict) for row in rows):
            raise WorldBankResponseError("Expected each result row to be an object")
        return metadata, rows, str(response.url.copy_with(query=None)), params

    async def _request(self, path: str, params: dict[str, str]) -> httpx.Response:
        client = self._require_client()
        try:
            response = await client.get(path, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise WorldBankHTTPError(str(exc)) from exc
        return response

    def _require_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Use WorldBankClient as an async context manager")
        return self._client


def _parse_indicator_summary(row: dict[str, Any], provenance: Provenance) -> IndicatorSummary:
    source = _required_mapping(row, "source")
    topics = row.get("topics") or []
    if not isinstance(topics, list):
        raise WorldBankResponseError("Expected indicator topics to be a list")
    topic_names: list[str] = []
    for topic in topics:
        if not isinstance(topic, dict):
            raise WorldBankResponseError("Expected indicator topic to be an object")
        topic_name = _optional_str(topic.get("value"))
        if topic_name is not None:
            topic_names.append(topic_name)
    return IndicatorSummary(
        code=_required_str(row, "id"),
        name=_required_str(row, "name"),
        unit=_optional_str(row.get("unit")),
        source_id=_required_str(source, "id"),
        source_name=_required_str(source, "value"),
        source_note=_optional_str(row.get("sourceNote")),
        source_organization=_optional_str(row.get("sourceOrganization")),
        topics=tuple(topic_names),
        provenance=provenance,
    )


def _parse_indicator_observation(
    row: dict[str, Any],
    indicator: IndicatorSummary,
    provenance: Provenance,
) -> IndicatorObservation:
    country = _required_mapping(row, "country")
    return IndicatorObservation(
        country_code=_required_str(row, "countryiso3code"),
        country_name=_required_str(country, "value"),
        indicator_code=indicator.code,
        indicator_name=indicator.name,
        year=int(_required_str(row, "date")),
        value=_optional_float(row.get("value")),
        unit=indicator.unit,
        source=indicator.source_name,
        source_note=indicator.source_note,
        provenance=provenance,
    )


def _parse_country_profile(row: dict[str, Any], provenance: Provenance) -> CountryProfile:
    region = _required_mapping(row, "region")
    income_level = _required_mapping(row, "incomeLevel")
    lending_type = _required_mapping(row, "lendingType")
    return CountryProfile(
        country_code=_required_str(row, "id"),
        iso2_code=_required_str(row, "iso2Code"),
        name=_required_str(row, "name"),
        region_code=_required_str(region, "id"),
        region_name=_required_str(region, "value"),
        income_level_code=_required_str(income_level, "id"),
        income_level_name=_required_str(income_level, "value"),
        lending_type_code=_required_str(lending_type, "id"),
        lending_type_name=_required_str(lending_type, "value"),
        capital_city=_optional_str(row.get("capitalCity")),
        longitude=_optional_float(row.get("longitude")),
        latitude=_optional_float(row.get("latitude")),
        provenance=provenance,
    )


def _is_worldbank_error(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("message"), list)
        and bool(payload["message"])
    )


def _clean_code(value: str) -> str:
    clean = value.strip().lower()
    if not clean:
        raise ValueError("country code must not be empty")
    return clean


def _clean_indicator_code(value: str) -> str:
    clean = value.strip().upper()
    if not clean:
        raise ValueError("indicator code must not be empty")
    return clean


def _required_mapping(row: dict[str, Any], key: str) -> dict[str, Any]:
    value = row.get(key)
    if not isinstance(value, dict):
        raise WorldBankResponseError(f"Expected {key} to be an object")
    return value


def _required_str(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or value == "":
        raise WorldBankResponseError(f"Expected non-empty string for {key}")
    return value


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise WorldBankResponseError("Expected optional string value")
    return value


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
