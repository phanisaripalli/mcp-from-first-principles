from __future__ import annotations

from typing import Any

from trade_intel.tools.registry import ToolDefinition, ToolRegistry
from trade_intel.tools.schemas import ArraySchema, IntegerSchema, StringSchema
from trade_intel.worldbank import WorldBankClient


def build_worldbank_tool_registry(client: WorldBankClient) -> ToolRegistry:
    return ToolRegistry(
        [
            ToolDefinition(
                name="search_development_indicators",
                description=(
                    "Search World Bank development indicator metadata by human words, "
                    "such as 'GDP', 'population', or 'exports'. Use this before "
                    "fetching indicator observations when the exact indicator code is unknown."
                ),
                input_schema={
                    "query": StringSchema(
                        "Human-readable indicator concept to search for."
                    ),
                    "limit": IntegerSchema(
                        "Maximum number of matching indicators to return.",
                        minimum=1,
                        maximum=25,
                    ),
                },
                executor=lambda arguments: client.search_indicators(
                    arguments["query"],
                    limit=arguments["limit"],
                ),
            ),
            ToolDefinition(
                name="get_development_indicator",
                description=(
                    "Fetch World Bank indicator observations for one or more countries "
                    "over a year range. Use ISO country codes such as DEU or USA and "
                    "a World Bank indicator code such as NY.GDP.MKTP.CD."
                ),
                input_schema={
                    "countries": ArraySchema(
                        "One or more ISO country codes.",
                        items=StringSchema("ISO country code such as DEU or USA."),
                    ),
                    "indicator": StringSchema(
                        "World Bank indicator code, for example NY.GDP.MKTP.CD."
                    ),
                    "start_year": IntegerSchema(
                        "First year to retrieve.",
                        minimum=1960,
                    ),
                    "end_year": IntegerSchema(
                        "Last year to retrieve.",
                        minimum=1960,
                    ),
                },
                executor=lambda arguments: client.get_indicator(
                    arguments["countries"],
                    arguments["indicator"],
                    arguments["start_year"],
                    arguments["end_year"],
                ),
            ),
            ToolDefinition(
                name="get_country_profile",
                description=(
                    "Fetch normalized World Bank metadata for a country, including "
                    "country code, region, income level, lending type, capital city, "
                    "and coordinates."
                ),
                input_schema={
                    "country": StringSchema(
                        "ISO country code or World Bank country code, such as DEU."
                    ),
                },
                executor=lambda arguments: client.get_country_profile(arguments["country"]),
            ),
        ]
    )


def poor_worldbank_tool_schema() -> dict[str, Any]:
    return {
        "name": "query_worldbank",
        "description": "Query World Bank.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "API path.",
                },
                "params": {
                    "type": "object",
                    "description": "Query parameters.",
                },
            },
            "required": ["path", "params"],
            "additionalProperties": False,
        },
    }

