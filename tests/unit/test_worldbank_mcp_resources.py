from __future__ import annotations

import asyncio
import json

import httpx
from mcp import Client

from trade_intel.mcp.worldbank_server import create_worldbank_mcp_server
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


def country_payload(code: str, iso2: str, name: str, capital: str) -> list[object]:
    return [
        {"page": 1, "pages": 1, "per_page": "50", "total": 1},
        [
            {
                "id": code,
                "iso2Code": iso2,
                "name": name,
                "region": {"id": "ECS", "value": "Europe & Central Asia"},
                "incomeLevel": {"id": "HIC", "value": "High income"},
                "lendingType": {"id": "LNX", "value": "Not classified"},
                "capitalCity": capital,
                "longitude": "13.4115",
                "latitude": "52.5235",
            }
        ],
    ]


def test_mcp_server_lists_concrete_country_resource() -> None:
    async def scenario():
        async with Client(create_worldbank_mcp_server(), raise_exceptions=True) as client:
            return await client.list_resources()

    result = run(scenario())

    assert [str(resource.uri) for resource in result.resources] == [
        "worldbank://countries/DEU"
    ]
    resource = result.resources[0]
    assert resource.name == "worldbank_country_deu"
    assert resource.title == "World Bank Country Profile: Germany"
    assert resource.mime_type == "application/json"


def test_mcp_server_lists_country_resource_template() -> None:
    async def scenario():
        async with Client(create_worldbank_mcp_server(), raise_exceptions=True) as client:
            return await client.list_resource_templates()

    result = run(scenario())

    assert [template.uri_template for template in result.resource_templates] == [
        "worldbank://countries/{country}"
    ]
    template = result.resource_templates[0]
    assert template.name == "worldbank_country_profile"
    assert "addressable reference context" in template.description


def test_mcp_client_reads_country_resource_by_uri() -> None:
    payloads = {
        "/v2/country/ind?format=json": country_payload(
            "IND",
            "IN",
            "India",
            "New Delhi",
        )
    }

    def client_factory():
        return WorldBankClient(transport=make_transport(payloads))

    async def scenario():
        server = create_worldbank_mcp_server(client_factory)
        async with Client(server, raise_exceptions=True) as client:
            return await client.read_resource("worldbank://countries/IND")

    result = run(scenario())

    assert result.contents[0].uri == "worldbank://countries/IND"
    assert result.contents[0].mime_type == "application/json"
    content = json.loads(result.contents[0].text)
    assert content["country_code"] == "IND"
    assert content["name"] == "India"
    assert content["capital_city"] == "New Delhi"
    assert content["provenance"]["source"] == "World Bank Indicators API"


def test_existing_mcp_tools_still_work_after_adding_resources() -> None:
    async def scenario():
        async with Client(create_worldbank_mcp_server(), raise_exceptions=True) as client:
            return await client.list_tools()

    result = run(scenario())

    assert [tool.name for tool in result.tools] == [
        "get_country_profile",
        "search_development_indicators",
        "get_development_indicator",
    ]
