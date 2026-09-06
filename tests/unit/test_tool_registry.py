from __future__ import annotations

import asyncio

import pytest

from trade_intel.tools import IntegerSchema, StringSchema, ToolDefinition, ToolRegistry


def run(coro):
    return asyncio.run(coro)


async def echo(arguments: dict[str, object]) -> dict[str, object]:
    return arguments


def test_lists_public_tool_schema() -> None:
    registry = ToolRegistry(
        [
            ToolDefinition(
                name="echo",
                description="Return the provided name and count.",
                input_schema={
                    "name": StringSchema("Name to echo."),
                    "count": IntegerSchema("Number of times.", minimum=1),
                },
                executor=echo,
            )
        ]
    )

    [schema] = registry.list_tools()

    assert schema["name"] == "echo"
    assert schema["description"] == "Return the provided name and count."
    assert schema["input_schema"]["required"] == ["name", "count"]
    assert schema["input_schema"]["properties"]["count"]["minimum"] == 1


def test_validates_missing_wrong_and_extra_arguments() -> None:
    registry = ToolRegistry(
        [
            ToolDefinition(
                name="echo",
                description="Return the provided name.",
                input_schema={"name": StringSchema("Name to echo.")},
                executor=echo,
            )
        ]
    )

    missing = run(registry.call_tool("echo", {}))
    wrong_type = run(registry.call_tool("echo", {"name": 123}))
    extra = run(registry.call_tool("echo", {"name": "Ada", "unused": True}))

    assert missing.ok is False
    assert missing.error == "Missing required argument: name"
    assert wrong_type.ok is False
    assert wrong_type.error == "name must be a string"
    assert extra.ok is False
    assert extra.error == "Unexpected argument(s): unused"


def test_unknown_tool_returns_structured_error() -> None:
    result = run(ToolRegistry().call_tool("missing", {}))

    assert result.ok is False
    assert result.tool_name == "missing"
    assert result.error == "Unknown tool: missing"


def test_duplicate_tool_names_are_rejected() -> None:
    tool = ToolDefinition(
        name="echo",
        description="Return the provided name.",
        input_schema={"name": StringSchema("Name to echo.")},
        executor=echo,
    )

    with pytest.raises(ValueError, match="Tool already registered"):
        ToolRegistry([tool, tool])

