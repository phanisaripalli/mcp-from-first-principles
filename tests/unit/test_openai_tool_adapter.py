from __future__ import annotations

import asyncio

from trade_intel.llm.tool_adapter import discover_openai_tools
from trade_intel.mcp.trade_server import create_trade_mcp_server
from trade_intel.mcp.worldbank_server import create_worldbank_mcp_server


def run(coro):
    return asyncio.run(coro)


def test_discovers_mcp_tools_as_openai_function_tools() -> None:
    async def scenario():
        return await discover_openai_tools(
            {
                "worldbank": create_worldbank_mcp_server(),
                "trade": create_trade_mcp_server(),
            }
        )

    specs, router = run(scenario())

    names = [spec.openai_name for spec in specs]
    assert "worldbank__get_country_profile" in names
    assert "worldbank__get_development_indicator" in names
    assert "trade__get_imports" in names
    assert all(spec.tool["type"] == "function" for spec in specs)
    assert all(spec.tool["parameters"]["type"] == "object" for spec in specs)
    assert router.route_for("trade__get_imports").server_label == "trade"


def test_openai_tool_names_are_prefixed_by_server() -> None:
    async def scenario():
        specs, _router = await discover_openai_tools(
            {
                "worldbank": create_worldbank_mcp_server(),
                "trade": create_trade_mcp_server(),
            }
        )
        return specs

    specs = run(scenario())

    assert {spec.openai_name.split("__", 1)[0] for spec in specs} == {"worldbank", "trade"}
    assert len({spec.openai_name for spec in specs}) == len(specs)
