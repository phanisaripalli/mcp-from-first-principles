from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Any, Callable

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from trade_intel.serialization import to_jsonable
from trade_intel.trade import TradeClient
from trade_intel.trade.errors import TradeDataError


ClientFactory = Callable[[], AbstractAsyncContextManager[TradeClient]]


def create_trade_mcp_server(
    client_factory: ClientFactory | None = None,
) -> MCPServer:
    make_client = client_factory or TradeClient
    server = MCPServer(
        "Trade Intelligence",
        version="0.1.0",
        instructions=(
            "Use these tools for HS product-code lookup and UN Comtrade "
            "import-flow questions. Returned data includes provenance and "
            "uses the no-key public preview API in this milestone."
        ),
    )

    @server.tool(
        name="find_product_code",
        title="Find HS Product Code",
        description=(
            "Search UN Comtrade HS product-code reference data by a human "
            "product description, such as lithium-ion batteries. Return "
            "candidate codes instead of silently guessing."
        ),
        structured_output=True,
    )
    async def find_product_code(query: str, limit: int = 10) -> dict[str, Any]:
        if limit < 1 or limit > 25:
            raise ToolError("limit must be between 1 and 25")
        try:
            async with make_client() as client:
                candidates = await client.find_product_code(query, limit=limit)
        except TradeDataError as exc:
            raise ToolError(str(exc)) from exc
        return {"candidates": to_jsonable(candidates)}

    @server.tool(
        name="get_imports",
        title="Get Imports",
        description=(
            "Fetch annual UN Comtrade import flows for an importer country, "
            "HS product code, and year. Use ISO3 country codes such as DEU. "
            "Optionally filter to one exporter ISO3 code such as CHN."
        ),
        structured_output=True,
    )
    async def get_imports(
        importer: str,
        hs_code: str,
        year: int,
        exporter: str | None = None,
    ) -> dict[str, Any]:
        if year < 1962:
            raise ToolError("year must be 1962 or later")
        try:
            async with make_client() as client:
                flow = await client.get_imports(
                    importer,
                    hs_code,
                    year,
                    exporter=exporter,
                )
        except TradeDataError as exc:
            raise ToolError(str(exc)) from exc
        return to_jsonable(flow)

    return server


mcp = create_trade_mcp_server()


if __name__ == "__main__":
    mcp.run()

