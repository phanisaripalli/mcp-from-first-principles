from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from mcp.server import MCPServer
from openai import OpenAI

from trade_intel.llm.openai_host import (
    DEFAULT_MODEL,
    ResponsesClient,
    _function_calls,
    _parse_arguments,
)
from trade_intel.llm.tool_adapter import discover_openai_tools


@dataclass(frozen=True)
class AgentStep:
    iteration: int
    selected_tool: str
    selected_server: str
    selected_mcp_tool: str
    arguments: dict[str, Any]
    mcp_result: dict[str, Any]


@dataclass(frozen=True)
class AgentLoopTrace:
    question: str
    model: str
    max_iterations: int
    available_tools: list[dict[str, Any]]
    steps: list[AgentStep]
    final_answer: str
    stopped_reason: str


class PlainPythonAgentLoop:
    def __init__(
        self,
        *,
        servers: dict[str, MCPServer],
        model: str | None = None,
        client: ResponsesClient | None = None,
        max_iterations: int = 5,
        max_tool_calls_per_iteration: int = 2,
    ) -> None:
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        if max_tool_calls_per_iteration < 1:
            raise ValueError("max_tool_calls_per_iteration must be at least 1")
        self._servers = servers
        self._model = model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL
        self._client = client or OpenAI()
        self._max_iterations = max_iterations
        self._max_tool_calls_per_iteration = max_tool_calls_per_iteration

    async def answer(self, question: str) -> AgentLoopTrace:
        tool_specs, router = await discover_openai_tools(self._servers)
        openai_tools = [spec.tool for spec in tool_specs]
        steps: list[AgentStep] = []

        previous_response_id: str | None = None
        next_input: list[dict[str, Any]] = _initial_input(question)

        for iteration in range(1, self._max_iterations + 1):
            kwargs: dict[str, Any] = {
                "model": self._model,
                "input": next_input,
                "tools": openai_tools,
                "tool_choice": "auto",
            }
            if previous_response_id is not None:
                kwargs["previous_response_id"] = previous_response_id

            response = self._client.responses.create(**kwargs)
            previous_response_id = response.id
            calls = _function_calls(response)

            if not calls:
                final_answer = getattr(response, "output_text", "") or ""
                return AgentLoopTrace(
                    question=question,
                    model=self._model,
                    max_iterations=self._max_iterations,
                    available_tools=openai_tools,
                    steps=steps,
                    final_answer=final_answer,
                    stopped_reason="final_answer",
                )

            if len(calls) > self._max_tool_calls_per_iteration:
                return self._stopped(
                    question,
                    openai_tools,
                    steps,
                    (
                        "too_many_tool_calls",
                        f"Model requested {len(calls)} tool calls in iteration {iteration}; "
                        f"this demo allows {self._max_tool_calls_per_iteration}.",
                    ),
                )

            outputs: list[dict[str, Any]] = []
            for call in calls:
                try:
                    arguments = _parse_arguments(call.arguments)
                    route = router.route_for(call.name)
                    mcp_result = await router.call_openai_tool(call.name, arguments)
                except Exception as exc:
                    return self._stopped(
                        question,
                        openai_tools,
                        steps,
                        ("tool_request_error", str(exc)),
                    )

                steps.append(
                    AgentStep(
                        iteration=iteration,
                        selected_tool=call.name,
                        selected_server=route.server_label,
                        selected_mcp_tool=route.mcp_name,
                        arguments=arguments,
                        mcp_result=mcp_result,
                    )
                )
                outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(mcp_result, default=str),
                    }
                )

            next_input = outputs

        final_answer = self._synthesize_after_max_iterations(
            question=question,
            previous_response_id=previous_response_id,
            pending_tool_outputs=next_input,
        )
        return AgentLoopTrace(
            question=question,
            model=self._model,
            max_iterations=self._max_iterations,
            available_tools=openai_tools,
            steps=steps,
            final_answer=final_answer,
            stopped_reason="max_iterations",
        )

    def _stopped(
        self,
        question: str,
        openai_tools: list[dict[str, Any]],
        steps: list[AgentStep],
        reason_and_answer: tuple[str, str],
    ) -> AgentLoopTrace:
        reason, answer = reason_and_answer
        return AgentLoopTrace(
            question=question,
            model=self._model,
            max_iterations=self._max_iterations,
            available_tools=openai_tools,
            steps=steps,
            final_answer=answer,
            stopped_reason=reason,
        )

    def _synthesize_after_max_iterations(
        self,
        *,
        question: str,
        previous_response_id: str | None,
        pending_tool_outputs: list[dict[str, Any]],
    ) -> str:
        if previous_response_id is None or not pending_tool_outputs:
            return f"Stopped after {self._max_iterations} iterations before any tool result was available."

        synthesis_input = list(pending_tool_outputs)
        synthesis_input.append(
            {
                "role": "developer",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "The host has reached its tool-use iteration limit. "
                            "Do not request more tools. Write the best concise answer "
                            "you can from the observations already provided. Say what "
                            "is known, what remains uncertain, and mention that the "
                            "answer is based on partial progress if needed."
                        ),
                    }
                ],
            }
        )

        response = self._client.responses.create(
            model=self._model,
            previous_response_id=previous_response_id,
            input=synthesis_input,
        )
        final_answer = getattr(response, "output_text", "") or ""
        if final_answer:
            return final_answer
        return (
            f"Stopped after {self._max_iterations} iterations. "
            f"The loop collected {len(pending_tool_outputs)} final tool observation(s) "
            f"for: {question}"
        )


def _initial_input(question: str) -> list[dict[str, Any]]:
    return [
        {
            "role": "developer",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "You answer from tool results when relevant tools are available. "
                        "Call at most one tool in each response. After the host returns that "
                        "observation, decide whether another tool is needed or whether you can "
                        "answer. Prefer a final answer once the observations directly address "
                        "the question. Keep the sequence short and use the available MCP-derived "
                        "tools."
                    ),
                }
            ],
        },
        {
            "role": "user",
            "content": [{"type": "input_text", "text": question}],
        },
    ]
