from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mcp import Client
from mcp.server import MCPServer

from trade_intel.llm.routing import MCPToolRouter, RoutedTool


@dataclass(frozen=True)
class OpenAIToolSpec:
    server_label: str
    mcp_name: str
    openai_name: str
    tool: dict[str, Any]


async def discover_openai_tools(
    servers: dict[str, MCPServer],
) -> tuple[list[OpenAIToolSpec], MCPToolRouter]:
    router = MCPToolRouter(servers)
    specs: list[OpenAIToolSpec] = []

    for server_label, server in servers.items():
        async with Client(server, raise_exceptions=True) as client:
            discovered = await client.list_tools()

        for mcp_tool in discovered.tools:
            openai_name = f"{server_label}__{mcp_tool.name}"
            route = RoutedTool(
                openai_name=openai_name,
                server_label=server_label,
                mcp_name=mcp_tool.name,
            )
            router.add_route(route)
            specs.append(
                OpenAIToolSpec(
                    server_label=server_label,
                    mcp_name=mcp_tool.name,
                    openai_name=openai_name,
                    tool={
                        "type": "function",
                        "name": openai_name,
                        "description": (
                            f"[{server_label} MCP] {mcp_tool.description or ''}"
                        ).strip(),
                        "parameters": _openai_parameters(mcp_tool.input_schema),
                        "strict": False,
                    },
                )
            )

    return specs, router


def _openai_parameters(mcp_input_schema: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(mcp_input_schema)
    parameters.setdefault("type", "object")
    parameters.setdefault("properties", {})
    parameters.setdefault("required", [])
    parameters.setdefault("additionalProperties", False)
    return parameters

