from __future__ import annotations

import asyncio
import json
import sys

from mcp import Client

from trade_intel.mcp.trade_server import create_trade_mcp_server


def args_from_cli(args: list[str]) -> tuple[str, int, str | None]:
    if not args:
        return "DEU", 2023, "CHN"
    if len(args) not in (2, 3):
        raise ValueError("Usage: python examples/mcp_trade_demo.py [IMPORTER YEAR [EXPORTER]]")
    importer = args[0].strip().upper()
    year = int(args[1])
    exporter = args[2].strip().upper() if len(args) == 3 else None
    return importer, year, exporter


async def main(importer: str = "DEU", year: int = 2023, exporter: str | None = "CHN") -> None:
    server = create_trade_mcp_server()

    async with Client(server, raise_exceptions=True) as client:
        tools = await client.list_tools()
        print("Trade MCP tool discovery:")
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

        product_result = await client.call_tool(
            "find_product_code",
            {"query": "lithium-ion batteries", "limit": 5},
        )
        print("\nProduct-code lookup:")
        print(json.dumps(product_result.structured_content, indent=2, default=str))

        hs_code = product_result.structured_content["candidates"][0]["hs_code"]
        import_args = {
            "importer": importer,
            "hs_code": hs_code,
            "year": year,
            "exporter": exporter,
        }
        if exporter is None:
            import_args.pop("exporter")

        import_result = await client.call_tool("get_imports", import_args)
        print("\nImport lookup:")
        print(
            json.dumps(
                {
                    "is_error": import_result.is_error,
                    "content": [item.model_dump() for item in import_result.content],
                    "structured_content": import_result.structured_content,
                },
                indent=2,
                default=str,
            )
        )


if __name__ == "__main__":
    importer_code, import_year, exporter_code = args_from_cli(sys.argv[1:])
    asyncio.run(main(importer_code, import_year, exporter_code))

