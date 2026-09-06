from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from mcp import Client
from mcp.server import MCPServer


@dataclass(frozen=True)
class RoutedTool:
    openai_name: str
    server_label: str
    mcp_name: str


class MCPToolRouter:
    def __init__(self, servers: dict[str, MCPServer]) -> None:
        self._servers = dict(servers)
        self._routes: dict[str, RoutedTool] = {}

    def add_route(self, route: RoutedTool) -> None:
        if route.server_label not in self._servers:
            raise ValueError(f"Unknown MCP server label: {route.server_label}")
        if route.openai_name in self._routes:
            raise ValueError(f"Duplicate OpenAI tool name: {route.openai_name}")
        self._routes[route.openai_name] = route

    def route_for(self, openai_name: str) -> RoutedTool:
        route = self._routes.get(openai_name)
        if route is None:
            raise ValueError(f"Unknown OpenAI tool name: {openai_name}")
        return route

    async def call_openai_tool(self, openai_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        route = self.route_for(openai_name)
        server = self._servers[route.server_label]
        async with Client(server, raise_exceptions=True) as client:
            result = await client.call_tool(route.mcp_name, arguments)

        content = {
            "server_label": route.server_label,
            "mcp_tool": route.mcp_name,
            "is_error": result.is_error,
            "content": [item.model_dump() for item in result.content],
            "structured_content": result.structured_content,
        }
        return content

    async def call_openai_tool_json(self, openai_name: str, arguments: dict[str, Any]) -> str:
        return json.dumps(await self.call_openai_tool(openai_name, arguments), default=str)

