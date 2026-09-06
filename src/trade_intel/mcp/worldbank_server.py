from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Any, Callable

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from trade_intel.serialization import to_jsonable
from trade_intel.worldbank import WorldBankClient
from trade_intel.worldbank.errors import WorldBankError


ClientFactory = Callable[[], AbstractAsyncContextManager[WorldBankClient]]


def create_worldbank_mcp_server(
    client_factory: ClientFactory | None = None,
) -> MCPServer:
    make_client = client_factory or WorldBankClient
    server = MCPServer(
        "World Bank Economy",
        version="0.1.0",
        instructions=(
            "Use these tools for World Bank country metadata and development "
            "indicator discovery. Returned data includes provenance."
        ),
    )

    @server.tool(
        name="get_country_profile",
        title="Get Country Profile",
        description=(
            "Fetch normalized World Bank metadata for a country, including "
            "country code, region, income level, lending type, capital city, "
            "coordinates, and provenance. Use ISO country codes such as DEU, "
            "USA, IND, or CHN."
        ),
        structured_output=True,
    )
    async def get_country_profile(country: str) -> dict[str, Any]:
        try:
            async with make_client() as client:
                return to_jsonable(await client.get_country_profile(country))
        except WorldBankError as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(
        name="search_development_indicators",
        title="Search Development Indicators",
        description=(
            "Search World Bank development indicator metadata by human words, "
            "such as GDP, population, exports, or inflation. Use this when the "
            "exact World Bank indicator code is unknown."
        ),
        structured_output=True,
    )
    async def search_development_indicators(
        query: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        if limit < 1 or limit > 25:
            raise ToolError("limit must be between 1 and 25")
        try:
            async with make_client() as client:
                indicators = await client.search_indicators(query, limit=limit)
        except WorldBankError as exc:
            raise ToolError(str(exc)) from exc
        return {"indicators": to_jsonable(indicators)}

    return server


mcp = create_worldbank_mcp_server()


if __name__ == "__main__":
    mcp.run()
