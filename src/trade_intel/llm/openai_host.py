from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

from mcp.server import MCPServer
from openai import OpenAI

from trade_intel.llm.routing import MCPToolRouter
from trade_intel.llm.tool_adapter import OpenAIToolSpec, discover_openai_tools


DEFAULT_MODEL = "gpt-5-nano"


class ResponsesClient(Protocol):
    class ResponsesResource(Protocol):
        def create(self, **kwargs: Any) -> Any: ...

    responses: ResponsesResource


@dataclass(frozen=True)
class ToolCallTrace:
    question: str
    model: str
    available_tools: list[dict[str, Any]]
    selected_tool: str | None
    selected_server: str | None
    selected_mcp_tool: str | None
    arguments: dict[str, Any] | None
    mcp_result: dict[str, Any] | None
    final_answer: str


class OpenAIMCPHost:
    def __init__(
        self,
        *,
        servers: dict[str, MCPServer],
        model: str | None = None,
        client: ResponsesClient | None = None,
        max_tool_calls: int = 1,
    ) -> None:
        self._servers = servers
        self._model = model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL
        self._client = client or OpenAI()
        self._max_tool_calls = max_tool_calls

    async def answer(self, question: str) -> ToolCallTrace:
        tool_specs, router = await discover_openai_tools(self._servers)
        openai_tools = [spec.tool for spec in tool_specs]

        selection_response = self._client.responses.create(
            model=self._model,
            input=[
                {
                    "role": "developer",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You answer from tool results when a relevant tool is available. "
                                "Select at most one tool. If no tool is relevant, answer briefly."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": question}],
                },
            ],
            tools=openai_tools,
            tool_choice="auto",
        )

        calls = _function_calls(selection_response)
        if not calls:
            return ToolCallTrace(
                question=question,
                model=self._model,
                available_tools=openai_tools,
                selected_tool=None,
                selected_server=None,
                selected_mcp_tool=None,
                arguments=None,
                mcp_result=None,
                final_answer=getattr(selection_response, "output_text", "") or "",
            )
        if len(calls) > self._max_tool_calls:
            return ToolCallTrace(
                question=question,
                model=self._model,
                available_tools=openai_tools,
                selected_tool=None,
                selected_server=None,
                selected_mcp_tool=None,
                arguments=None,
                mcp_result=None,
                final_answer=(
                    "This demo supports exactly one model-selected tool call. "
                    f"The model requested {len(calls)} tool calls."
                ),
            )

        call = calls[0]
        arguments = _parse_arguments(call.arguments)
        route = router.route_for(call.name)
        mcp_result = await router.call_openai_tool(call.name, arguments)

        final_response = self._client.responses.create(
            model=self._model,
            previous_response_id=selection_response.id,
            input=[
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(mcp_result, default=str),
                }
            ],
        )

        return ToolCallTrace(
            question=question,
            model=self._model,
            available_tools=openai_tools,
            selected_tool=call.name,
            selected_server=route.server_label,
            selected_mcp_tool=route.mcp_name,
            arguments=arguments,
            mcp_result=mcp_result,
            final_answer=getattr(final_response, "output_text", "") or "",
        )


def _function_calls(response: Any) -> list[Any]:
    return [item for item in getattr(response, "output", []) if getattr(item, "type", None) == "function_call"]


def _parse_arguments(arguments: str) -> dict[str, Any]:
    parsed = json.loads(arguments or "{}")
    if not isinstance(parsed, dict):
        raise ValueError("Function-call arguments must decode to an object")
    return parsed


def default_model_from_env() -> str:
    return os.getenv("OPENAI_MODEL") or DEFAULT_MODEL

