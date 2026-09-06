from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Any, Callable

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ToolError

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

    async def get_country_profile_data(country: str) -> dict[str, Any]:
        async with make_client() as client:
            return to_jsonable(await client.get_country_profile(country))

    async def read_country_profile_tool(country: str) -> dict[str, Any]:
        try:
            return await get_country_profile_data(country)
        except WorldBankError as exc:
            raise ToolError(str(exc)) from exc

    async def read_country_profile_resource(country: str) -> dict[str, Any]:
        try:
            return await get_country_profile_data(country)
        except WorldBankError as exc:
            raise ResourceError(str(exc)) from exc

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
        return await read_country_profile_tool(country)

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

    @server.resource(
        "worldbank://countries/DEU",
        name="worldbank_country_deu",
        title="World Bank Country Profile: Germany",
        description=(
            "Concrete example of an addressable World Bank country profile "
            "resource. Read it for normalized Germany metadata and provenance."
        ),
        mime_type="application/json",
    )
    async def germany_country_profile() -> dict[str, Any]:
        return await read_country_profile_resource("DEU")

    @server.resource(
        "worldbank://countries/{country}",
        name="worldbank_country_profile",
        title="World Bank Country Profile",
        description=(
            "Read a normalized World Bank country profile by URI, for example "
            "worldbank://countries/IND. This is addressable reference context, "
            "not a search capability."
        ),
        mime_type="application/json",
    )
    async def country_profile_resource(country: str) -> dict[str, Any]:
        return await read_country_profile_resource(country)

    return server


mcp = create_worldbank_mcp_server()


if __name__ == "__main__":
    mcp.run()
