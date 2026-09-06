from __future__ import annotations

import asyncio
import json

import httpx

from trade_intel.tools.worldbank_tools import (
    build_worldbank_tool_registry,
    poor_worldbank_tool_schema,
)
from trade_intel.worldbank import WorldBankClient


def run(coro):
    return asyncio.run(coro)


def make_transport(payloads: dict[str, object]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.url.path}?{request.url.query.decode()}"
        payload = payloads.get(key)
        if payload is None:
            return httpx.Response(404, json={"message": [{"key": "not found", "value": key}]})
        return httpx.Response(200, content=json.dumps(payload).encode("utf-8"))

    return httpx.MockTransport(handler)


def test_worldbank_tool_registry_exposes_domain_specific_tools() -> None:
    async def scenario():
        async with WorldBankClient(transport=make_transport({})) as client:
            return build_worldbank_tool_registry(client).list_tools()

    tools = run(scenario())

    names = {tool["name"] for tool in tools}
    assert names == {
        "search_development_indicators",
        "get_development_indicator",
        "get_country_profile",
    }
    country_tool = next(tool for tool in tools if tool["name"] == "get_country_profile")
    assert "country" in country_tool["input_schema"]["properties"]
    assert "World Bank metadata" in country_tool["description"]


def test_get_country_profile_tool_executes_existing_client_and_returns_structured_result() -> None:
    payloads = {
        "/v2/country/deu?format=json": [
            {"page": 1, "pages": 1, "per_page": "50", "total": 1},
            [
                {
                    "id": "DEU",
                    "iso2Code": "DE",
                    "name": "Germany",
                    "region": {"id": "ECS", "value": "Europe & Central Asia"},
                    "incomeLevel": {"id": "HIC", "value": "High income"},
                    "lendingType": {"id": "LNX", "value": "Not classified"},
                    "capitalCity": "Berlin",
                    "longitude": "13.4115",
                    "latitude": "52.5235",
                }
            ],
        ]
    }

    async def scenario():
        async with WorldBankClient(transport=make_transport(payloads)) as client:
            registry = build_worldbank_tool_registry(client)
            return await registry.call_tool("get_country_profile", {"country": "DEU"})

    result = run(scenario())

    assert result.ok is True
    assert result.content["country_code"] == "DEU"
    assert result.content["name"] == "Germany"
    assert result.content["provenance"]["source"] == "World Bank Indicators API"


def test_tool_validation_stops_bad_arguments_before_client_call() -> None:
    async def scenario():
        async with WorldBankClient(transport=make_transport({})) as client:
            registry = build_worldbank_tool_registry(client)
            return await registry.call_tool("get_country_profile", {})

    result = run(scenario())

    assert result.ok is False
    assert result.error == "Missing required argument: country"


def test_poor_tool_schema_leaks_api_details() -> None:
    schema = poor_worldbank_tool_schema()

    assert schema["name"] == "query_worldbank"
    assert set(schema["input_schema"]["properties"]) == {"path", "params"}
    assert schema["description"] == "Query World Bank."

