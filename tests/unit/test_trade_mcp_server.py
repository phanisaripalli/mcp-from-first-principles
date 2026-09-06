from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
from mcp import Client

from trade_intel.mcp.trade_server import create_trade_mcp_server
from trade_intel.trade import TradeClient


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


def payloads() -> dict[str, object]:
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
        "/public/v1/preview/C/A/HS?flowCode=M&reporterCode=276&period=2023&cmdCode=850760&partnerCode=156&breakdownMode=classic": {
            "elapsedTime": "0.2 secs",
            "count": 1,
            "data": [{"primaryValue": 100.0}],
        },
    }


def test_trade_mcp_server_discovers_trade_tools() -> None:
    async def scenario():
        async with Client(create_trade_mcp_server(), raise_exceptions=True) as client:
            return await client.list_tools()

    result = run(scenario())

    assert [tool.name for tool in result.tools] == ["find_product_code", "get_imports"]
    assert "UN Comtrade HS product-code" in result.tools[0].description
    assert "importer" in result.tools[1].input_schema["properties"]


def test_trade_mcp_server_does_not_import_worldbank_server() -> None:
    source = Path("src/trade_intel/mcp/trade_server.py").read_text()

    assert "worldbank" not in source.lower()


def test_trade_mcp_server_invokes_product_code_lookup() -> None:
    def client_factory():
        return TradeClient(transport=make_transport(payloads()))

    async def scenario():
        server = create_trade_mcp_server(client_factory)
        async with Client(server, raise_exceptions=True) as client:
            return await client.call_tool(
                "find_product_code",
                {"query": "lithium-ion batteries", "limit": 5},
            )

    result = run(scenario())

    assert result.is_error is False
    assert result.structured_content["candidates"][0]["hs_code"] == "850760"


def test_trade_mcp_server_invokes_import_lookup() -> None:
    def client_factory():
        return TradeClient(transport=make_transport(payloads()))

    async def scenario():
        server = create_trade_mcp_server(client_factory)
        async with Client(server, raise_exceptions=True) as client:
            return await client.call_tool(
                "get_imports",
                {
                    "importer": "DEU",
                    "hs_code": "850760",
                    "year": 2023,
                    "exporter": "CHN",
                },
            )

    result = run(scenario())

    assert result.is_error is False
    assert result.structured_content["importer_code"] == "DEU"
    assert result.structured_content["exporter_code"] == "CHN"
    assert result.structured_content["trade_value_usd"] == 100.0
    assert result.structured_content["provenance"]["source"] == (
        "UN Comtrade public preview API"
    )
