from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from trade_intel.worldbank import WorldBankClient
from trade_intel.worldbank.errors import WorldBankAPIError, WorldBankNotFoundError


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


def test_get_country_profile_normalizes_country_payload() -> None:
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
            return await client.get_country_profile("DEU")

    profile = run(scenario())

    assert profile.country_code == "DEU"
    assert profile.name == "Germany"
    assert profile.longitude == pytest.approx(13.4115)
    assert profile.provenance.source == "World Bank Indicators API"
    assert profile.provenance.total == 1


def test_get_indicator_fetches_metadata_and_observations() -> None:
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
        "/v2/country/deu/indicator/NY.GDP.MKTP.CD?format=json&date=2022%3A2023&per_page=20000": [
            {"page": 1, "pages": 1, "per_page": "20000", "total": 2},
            [
                {
                    "countryiso3code": "DEU",
                    "country": {"id": "DE", "value": "Germany"},
                    "date": "2023",
                    "value": 4456081016096.69,
                },
                {
                    "countryiso3code": "DEU",
                    "country": {"id": "DE", "value": "Germany"},
                    "date": "2022",
                    "value": None,
                },
            ],
        ],
    }

    async def scenario():
        async with WorldBankClient(transport=make_transport(payloads)) as client:
            return await client.get_indicator(["DEU"], "NY.GDP.MKTP.CD", 2022, 2023)

    observations = run(scenario())

    assert [observation.year for observation in observations] == [2023, 2022]
    assert observations[0].value == pytest.approx(4456081016096.69)
    assert observations[1].value is None
    assert observations[0].source_note == "GDP at purchaser's prices."
    assert observations[0].provenance.query_params["date"] == "2022:2023"


def test_search_indicators_matches_name_code_and_source_note() -> None:
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

    async def scenario():
        async with WorldBankClient(transport=make_transport(payloads)) as client:
            return await client.search_indicators("gdp")

    matches = run(scenario())

    assert [match.code for match in matches] == ["NY.GDP.MKTP.CD"]
    assert matches[0].topics == ("Economy & Growth",)


def test_search_indicators_ignores_empty_topic_labels() -> None:
    payloads = {
        "/v2/indicator?format=json&per_page=100&page=1": [
            {"page": 1, "pages": 1, "per_page": "100", "total": 1},
            [
                {
                    "id": "NY.GDP.MKTP.CD",
                    "name": "GDP (current US$)",
                    "unit": "",
                    "source": {"id": "2", "value": "World Development Indicators"},
                    "sourceNote": "GDP at purchaser's prices.",
                    "sourceOrganization": "World Bank.",
                    "topics": [
                        {"id": "3", "value": "Economy & Growth"},
                        {"id": "", "value": ""},
                    ],
                },
            ],
        ]
    }

    async def scenario():
        async with WorldBankClient(transport=make_transport(payloads)) as client:
            return await client.search_indicators("gdp")

    matches = run(scenario())

    assert matches[0].topics == ("Economy & Growth",)


def test_worldbank_api_error_is_raised() -> None:
    payloads = {
        "/v2/country/not-a-code?format=json": {
            "message": [{"key": "Invalid value", "value": "The parameter value is invalid"}]
        }
    }

    async def scenario():
        async with WorldBankClient(transport=make_transport(payloads)) as client:
            await client.get_country_profile("not-a-code")

    with pytest.raises(WorldBankAPIError):
        run(scenario())


def test_empty_indicator_observations_raise_not_found() -> None:
    indicator_payload = [
        {"page": 1, "pages": 1, "per_page": "50", "total": 1},
        [
            {
                "id": "SP.POP.TOTL",
                "name": "Population, total",
                "unit": "",
                "source": {"id": "2", "value": "World Development Indicators"},
                "sourceNote": "",
                "sourceOrganization": "",
                "topics": [],
            }
        ],
    ]
    payloads = {
        "/v2/indicator/SP.POP.TOTL?format=json": indicator_payload,
        "/v2/country/deu/indicator/SP.POP.TOTL?format=json&date=1800%3A1801&per_page=20000": [
            {"page": 1, "pages": 1, "per_page": "20000", "total": 0},
            [],
        ],
    }

    async def scenario():
        async with WorldBankClient(transport=make_transport(payloads)) as client:
            await client.get_indicator(["DEU"], "SP.POP.TOTL", 1800, 1801)

    with pytest.raises(WorldBankNotFoundError):
        run(scenario())
