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

        resources = await client.list_resources()
        print("\nMCP resource discovery:")
        print(
            json.dumps(
                [
                    {
                        "uri": str(resource.uri),
                        "name": resource.name,
                        "title": resource.title,
                        "description": resource.description,
                        "mime_type": resource.mime_type,
                    }
                    for resource in resources.resources
                ],
                indent=2,
            )
        )

        templates = await client.list_resource_templates()
        print("\nMCP resource template discovery:")
        print(
            json.dumps(
                [
                    {
                        "uri_template": template.uri_template,
                        "name": template.name,
                        "title": template.title,
                        "description": template.description,
                        "mime_type": template.mime_type,
                    }
                    for template in templates.resource_templates
                ],
                indent=2,
            )
        )

        resource_uri = f"worldbank://countries/{country}"
        resource = await client.read_resource(resource_uri)
        print(f"\nMCP resource read: {resource_uri}")
        print(resource.contents[0].text)

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
