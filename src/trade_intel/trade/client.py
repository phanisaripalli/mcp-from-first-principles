from __future__ import annotations

from typing import Any

import httpx

from trade_intel.provenance import Provenance
from trade_intel.trade.errors import (
    TradeDataHTTPError,
    TradeDataNotFoundError,
    TradeDataResponseError,
)
from trade_intel.trade.models import CountryCode, ProductCodeCandidate, TradeFlow
from trade_intel.trade.reference import (
    parse_country_codes,
    parse_product_codes,
    rank_product_matches,
)


class TradeClient:
    """Small async client for UN Comtrade public preview and reference data."""

    def __init__(
        self,
        *,
        base_url: str = "https://comtradeapi.un.org",
        timeout: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport
        self._client: httpx.AsyncClient | None = None
        self._reporters: list[CountryCode] | None = None
        self._partners: list[CountryCode] | None = None
        self._products: list[ProductCodeCandidate] | None = None

    async def __aenter__(self) -> "TradeClient":
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

    async def find_product_code(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> list[ProductCodeCandidate]:
        if limit < 1 or limit > 25:
            raise ValueError("limit must be between 1 and 25")
        products = await self._get_products()
        return rank_product_matches(products, query, limit=limit)

    async def get_imports(
        self,
        importer: str,
        hs_code: str,
        year: int,
        *,
        exporter: str | None = None,
    ) -> TradeFlow:
        importer_code = await self._resolve_reporter(importer)
        exporter_code = await self._resolve_partner(exporter) if exporter else _world_partner()
        product = await self._find_exact_product(hs_code)
        params = {
            "flowCode": "M",
            "reporterCode": str(importer_code.code),
            "period": str(year),
            "cmdCode": product.hs_code,
            "partnerCode": str(exporter_code.code),
            "breakdownMode": "classic",
        }
        endpoint = "/public/v1/preview/C/A/HS"
        payload, response_url = await self._get_json(endpoint, params)
        rows = payload.get("data")
        if not isinstance(rows, list):
            raise TradeDataResponseError("Expected Comtrade preview response with data")
        if not rows:
            raise TradeDataNotFoundError(
                f"No import rows found for {importer} {hs_code} in {year}"
            )

        total_value = 0.0
        for row in rows:
            if not isinstance(row, dict):
                raise TradeDataResponseError("Expected trade data rows to be objects")
            total_value += _optional_float(row.get("primaryValue")) or 0.0

        metadata = {
            "elapsed_time": _optional_str(payload.get("elapsedTime")),
            "row_count": _optional_int(payload.get("count")),
            "preview_record_limit": 500,
            "breakdown_mode": "classic",
            "uses_subscription_key": False,
        }
        provenance = Provenance(
            source="UN Comtrade public preview API",
            endpoint=response_url,
            query_params=params,
            total=len(rows),
            notes=(
                "Public preview endpoint; capped at 500 records and not suitable "
                "for production-scale analysis."
            ),
        )
        return TradeFlow(
            importer_code=importer_code.iso3,
            importer_name=importer_code.name,
            importer_comtrade_code=importer_code.code,
            exporter_code=None if exporter_code.code == 0 else exporter_code.iso3,
            exporter_name=exporter_code.name,
            exporter_comtrade_code=exporter_code.code,
            hs_code=product.hs_code,
            product_description=product.description,
            year=year,
            flow="imports",
            trade_value_usd=total_value,
            source="UN Comtrade public preview API",
            source_query_metadata=metadata,
            provenance=provenance,
        )

    async def _get_products(self) -> list[ProductCodeCandidate]:
        if self._products is None:
            endpoint = "/files/v1/app/reference/HS.json"
            payload, response_url = await self._get_json(endpoint, {})
            self._products = parse_product_codes(payload, endpoint=response_url)
        return self._products

    async def _get_reporters(self) -> list[CountryCode]:
        if self._reporters is None:
            endpoint = "/files/v1/app/reference/Reporters.json"
            payload, response_url = await self._get_json(endpoint, {})
            self._reporters = parse_country_codes(
                payload,
                endpoint=response_url,
                role="reporter",
            )
        return self._reporters

    async def _get_partners(self) -> list[CountryCode]:
        if self._partners is None:
            endpoint = "/files/v1/app/reference/partnerAreas.json"
            payload, response_url = await self._get_json(endpoint, {})
            self._partners = parse_country_codes(
                payload,
                endpoint=response_url,
                role="partner",
            )
        return self._partners

    async def _resolve_reporter(self, iso3: str) -> CountryCode:
        return _find_country(await self._get_reporters(), iso3, role="reporter")

    async def _resolve_partner(self, iso3: str) -> CountryCode:
        return _find_country(await self._get_partners(), iso3, role="partner")

    async def _find_exact_product(self, hs_code: str) -> ProductCodeCandidate:
        clean = hs_code.strip()
        products = await self._get_products()
        for product in products:
            if product.hs_code == clean:
                return product
        raise TradeDataNotFoundError(f"HS product code not found: {hs_code}")

    async def _get_json(
        self,
        path: str,
        params: dict[str, str],
    ) -> tuple[dict[str, Any], str]:
        client = self._require_client()
        try:
            response = await client.get(path, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TradeDataHTTPError(str(exc)) from exc

        payload = response.json()
        if not isinstance(payload, dict):
            raise TradeDataResponseError("Expected Comtrade response to be an object")
        return payload, str(response.url.copy_with(query=None))

    def _require_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Use TradeClient as an async context manager")
        return self._client


def _find_country(codes: list[CountryCode], iso3: str, *, role: str) -> CountryCode:
    clean = iso3.strip().upper()
    if not clean:
        raise ValueError(f"{role} country code must not be empty")
    matching = [code for code in codes if code.iso3 == clean]
    matching.sort(key=lambda code: code.entry_expired_date is not None)
    for code in matching:
        if code.iso3 == clean:
            return code
    raise TradeDataNotFoundError(f"UN Comtrade {role} not found for ISO3 code: {iso3}")


def _world_partner() -> CountryCode:
    return CountryCode(
        code=0,
        iso3="WLD",
        name="World",
        role="partner",
        entry_expired_date=None,
        provenance=Provenance(
            source="UN Comtrade convention",
            endpoint="internal:world-partner",
            query_params={},
            notes="UN Comtrade partnerCode 0 represents World aggregate.",
        ),
    )


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
