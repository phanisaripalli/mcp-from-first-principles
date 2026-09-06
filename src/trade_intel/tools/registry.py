from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from trade_intel.serialization import to_jsonable
from trade_intel.tools.schemas import InputSchema


ToolExecutor = Callable[[dict[str, Any]], Awaitable[Any]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, InputSchema]
    executor: ToolExecutor

    def public_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    name: schema.to_json_schema()
                    for name, schema in self.input_schema.items()
                },
                "required": list(self.input_schema),
                "additionalProperties": False,
            },
        }

    def validate_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        unexpected = sorted(set(arguments) - set(self.input_schema))
        if unexpected:
            raise ValueError(f"Unexpected argument(s): {', '.join(unexpected)}")

        validated: dict[str, Any] = {}
        for name, schema in self.input_schema.items():
            if name not in arguments:
                raise ValueError(f"Missing required argument: {name}")
            validated[name] = schema.validate(name, arguments[name])
        return validated


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    ok: bool
    content: Any | None = None
    error: str | None = None


class ToolRegistry:
    def __init__(self, tools: list[ToolDefinition] | None = None) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def list_tools(self) -> list[dict[str, Any]]:
        return [tool.public_schema() for tool in self._tools.values()]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(tool_name=name, ok=False, error=f"Unknown tool: {name}")
        try:
            validated = tool.validate_arguments(arguments)
            content = await tool.executor(validated)
        except Exception as exc:
            return ToolResult(tool_name=name, ok=False, error=str(exc))
        return ToolResult(tool_name=name, ok=True, content=to_jsonable(content))
