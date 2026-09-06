from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from trade_intel.trade import TradeClient
from trade_intel.trade.errors import TradeDataNotFoundError


def run(coro):
    return asyncio.run(coro)


def make_transport(payloads: dict[str, object]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.url.path}?{request.url.query.decode()}"
        payload = payloads.get(key)
        if payload is None:
            return httpx.Response(404, json={"message": f"not found: {key}"})
        return httpx.Response(200, content=json.dumps(payload).encode("utf-8"))

    return httpx.MockTransport(handler)


def reference_payloads() -> dict[str, object]:
    return {
        "/files/v1/app/reference/Reporters.json?": {
            "results": [
                {
                    "reporterCode": 276,
                    "reporterDesc": "Germany",
                    "reporterCodeIsoAlpha3": "DEU",
                }
            ]
        },
        "/files/v1/app/reference/partnerAreas.json?": {
            "results": [
                {
                    "PartnerCode": 156,
                    "PartnerDesc": "China",
                    "PartnerCodeIsoAlpha3": "CHN",
                }
            ]
        },
        "/files/v1/app/reference/HS.json?": {
            "className": "Combined HS",
            "results": [
                {
                    "id": "850760",
                    "text": "850760 - Electric accumulators; lithium-ion",
                    "parent": "8507",
                    "isLeaf": "1",
                    "aggrLevel": 6,
                    "standardUnitAbbr": "u",
                }
            ],
        },
    }


def test_get_imports_normalizes_and_sums_preview_rows() -> None:
    payloads = reference_payloads()
    payloads[
        "/public/v1/preview/C/A/HS?flowCode=M&reporterCode=276&period=2023&cmdCode=850760&partnerCode=156&breakdownMode=classic"
    ] = {
        "elapsedTime": "0.2 secs",
        "count": 2,
        "data": [
            {"primaryValue": 2454.255},
            {"primaryValue": 777.522},
        ],
    }

    async def scenario():
        async with TradeClient(transport=make_transport(payloads)) as client:
            return await client.get_imports(
                "DEU",
                "850760",
                2023,
                exporter="CHN",
            )

    flow = run(scenario())

    assert flow.importer_code == "DEU"
    assert flow.exporter_code == "CHN"
    assert flow.hs_code == "850760"
    assert flow.trade_value_usd == pytest.approx(3231.777)
    assert flow.source_query_metadata["row_count"] == 2
    assert flow.source_query_metadata["preview_record_limit"] == 500
    assert flow.source_query_metadata["breakdown_mode"] == "classic"
    assert flow.provenance.source == "UN Comtrade public preview API"


def test_get_imports_uses_world_partner_when_exporter_is_omitted() -> None:
    payloads = reference_payloads()
    payloads[
        "/public/v1/preview/C/A/HS?flowCode=M&reporterCode=276&period=2023&cmdCode=850760&partnerCode=0&breakdownMode=classic"
    ] = {
        "elapsedTime": "0.2 secs",
        "count": 1,
        "data": [{"primaryValue": 100.0}],
    }

    async def scenario():
        async with TradeClient(transport=make_transport(payloads)) as client:
            return await client.get_imports("DEU", "850760", 2023)

    flow = run(scenario())

    assert flow.exporter_code is None
    assert flow.exporter_name == "World"
    assert flow.exporter_comtrade_code == 0


def test_get_imports_raises_for_missing_rows() -> None:
    payloads = reference_payloads()
    payloads[
        "/public/v1/preview/C/A/HS?flowCode=M&reporterCode=276&period=2023&cmdCode=850760&partnerCode=0&breakdownMode=classic"
    ] = {
        "elapsedTime": "0.1 secs",
        "count": 0,
        "data": [],
    }

    async def scenario():
        async with TradeClient(transport=make_transport(payloads)) as client:
            await client.get_imports("DEU", "850760", 2023)

    with pytest.raises(TradeDataNotFoundError):
        run(scenario())
