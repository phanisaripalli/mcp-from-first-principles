from __future__ import annotations

import asyncio
import json
import sys

from mcp import Client

from trade_intel.mcp.worldbank_server import create_worldbank_mcp_server


def country_from_args(args: list[str]) -> str:
    if not args:
        return "DEU"
    if len(args) > 1:
        raise ValueError("Usage: python examples/mcp_worldbank_demo.py [COUNTRY_CODE]")
    return args[0].strip().upper()


async def main(country: str = "DEU") -> None:
    server = create_worldbank_mcp_server()

    async with Client(server, raise_exceptions=True) as client:
        tools = await client.list_tools()
        print("MCP tool discovery:")
        print(
            json.dumps(
                [
                    {
                        "name": tool.name,
                        "title": tool.title,
                        "description": tool.description,
                        "input_schema": tool.input_schema,
                    }
                    for tool in tools.tools
                ],
                indent=2,
            )
        )

        result = await client.call_tool("get_country_profile", {"country": country})
        print("\nMCP tool invocation:")
        print(
            json.dumps(
                {
                    "is_error": result.is_error,
                    "content": [item.model_dump() for item in result.content],
                    "structured_content": result.structured_content,
                },
                indent=2,
                default=str,
            )
        )


if __name__ == "__main__":
    asyncio.run(main(country_from_args(sys.argv[1:])))
