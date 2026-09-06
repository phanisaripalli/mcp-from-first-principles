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


def test_mcp_server_exposes_tool_discovery_schema() -> None:
    async def scenario():
        async with Client(create_worldbank_mcp_server(), raise_exceptions=True) as client:
            return await client.list_tools()

    result = run(scenario())

    tool_names = [tool.name for tool in result.tools]
    assert tool_names == [
        "get_country_profile",
        "search_development_indicators",
        "get_development_indicator",
    ]
    country_tool = result.tools[0]
    assert country_tool.title == "Get Country Profile"
    assert "World Bank metadata" in country_tool.description
    assert country_tool.input_schema["properties"]["country"]["type"] == "string"


def test_mcp_server_invokes_existing_worldbank_client() -> None:
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

    def client_factory():
        return WorldBankClient(transport=make_transport(payloads))

    async def scenario():
        server = create_worldbank_mcp_server(client_factory)
        async with Client(server, raise_exceptions=True) as client:
            return await client.call_tool("get_country_profile", {"country": "DEU"})

    result = run(scenario())

    assert result.is_error is False
    assert result.structured_content["country_code"] == "DEU"
    assert result.structured_content["name"] == "Germany"
    assert result.structured_content["provenance"]["source"] == "World Bank Indicators API"
    assert result.content[0].type == "text"


def test_mcp_server_invokes_indicator_search() -> None:
    payloads = {
        "/v2/indicator?format=json&per_page=100&page=1": [
            {"page": 1, "pages": 1, "per_page": "100", "total": 2},
            [
                {
                    "id": "SP.POP.TOTL",
                    "name": "Population, total",
                    "unit": "",
                    "source": {"id": "2", "value": "World Development Indicators"},
                    "sourceNote": "Total population is based on the de facto definition.",
                    "sourceOrganization": "World Bank.",
                    "topics": [],
                },
                {
                    "id": "NY.GDP.MKTP.CD",
                    "name": "GDP (current US$)",
                    "unit": "",
                    "source": {"id": "2", "value": "World Development Indicators"},
                    "sourceNote": "GDP at purchaser's prices.",
                    "sourceOrganization": "World Bank.",
                    "topics": [{"id": "3", "value": "Economy & Growth"}],
                },
            ],
        ]
    }

    def client_factory():
        return WorldBankClient(transport=make_transport(payloads))

    async def scenario():
        server = create_worldbank_mcp_server(client_factory)
        async with Client(server, raise_exceptions=True) as client:
            return await client.call_tool(
                "search_development_indicators",
                {"query": "gdp", "limit": 5},
            )

    result = run(scenario())

    assert result.is_error is False
    assert result.structured_content["indicators"][0]["code"] == "NY.GDP.MKTP.CD"
    assert result.structured_content["indicators"][0]["provenance"]["source"] == (
        "World Bank Indicators API"
    )


def test_mcp_server_invokes_development_indicator_lookup() -> None:
    indicator_payload = [
        {"page": 1, "pages": 1, "per_page": "50", "total": 1},
        [
            {
                "id": "NY.GDP.MKTP.CD",
                "name": "GDP (current US$)",
                "unit": "",
                "source": {"id": "2", "value": "World Development Indicators"},
                "sourceNote": "GDP at purchaser's prices.",
                "sourceOrganization": "World Bank national accounts data.",
                "topics": [{"id": "3", "value": "Economy & Growth"}],
            }
        ],
    ]
    payloads = {
        "/v2/indicator/NY.GDP.MKTP.CD?format=json": indicator_payload,
        "/v2/country/deu/indicator/NY.GDP.MKTP.CD?format=json&date=2023%3A2023&per_page=20000": [
            {"page": 1, "pages": 1, "per_page": "20000", "total": 1},
            [
                {
                    "countryiso3code": "DEU",
                    "country": {"id": "DE", "value": "Germany"},
                    "date": "2023",
                    "value": 4456081016096.69,
                }
            ],
        ],
    }

    def client_factory():
        return WorldBankClient(transport=make_transport(payloads))

    async def scenario():
        server = create_worldbank_mcp_server(client_factory)
        async with Client(server, raise_exceptions=True) as client:
            return await client.call_tool(
                "get_development_indicator",
                {
                    "countries": ["DEU"],
                    "indicator": "NY.GDP.MKTP.CD",
                    "start_year": 2023,
                    "end_year": 2023,
                },
            )

    result = run(scenario())

    assert result.is_error is False
    assert result.structured_content["observations"][0]["country_code"] == "DEU"
    assert result.structured_content["observations"][0]["indicator_code"] == "NY.GDP.MKTP.CD"


def test_mcp_tool_error_is_returned_as_tool_result() -> None:
    async def scenario():
        async with Client(create_worldbank_mcp_server(), raise_exceptions=True) as client:
            return await client.call_tool(
                "search_development_indicators",
                {"query": "gdp", "limit": 100},
            )

    result = run(scenario())

    assert result.is_error is True
    assert "limit must be between 1 and 25" in result.content[0].text


def test_worldbank_domain_error_is_returned_as_mcp_tool_error() -> None:
    def client_factory():
        return WorldBankClient(transport=make_transport({}))

    async def scenario():
        server = create_worldbank_mcp_server(client_factory)
        async with Client(server, raise_exceptions=True) as client:
            return await client.call_tool("get_country_profile", {"country": "ZZZ"})

    result = run(scenario())

    assert result.is_error is True
    assert "404 Not Found" in result.content[0].text
