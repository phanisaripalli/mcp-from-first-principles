from __future__ import annotations

import json
import os
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from mcp.server import MCPServer
from openai import OpenAI

from trade_intel.llm.agent_loop import AgentLoopTrace, AgentStep
from trade_intel.llm.openai_host import (
    DEFAULT_MODEL,
    ResponsesClient,
    _function_calls,
    _parse_arguments,
)
from trade_intel.llm.routing import MCPToolRouter
from trade_intel.llm.tool_adapter import discover_openai_tools


class LangGraphAgentState(TypedDict):
    question: str
    model: str
    max_iterations: int
    available_tools: list[dict[str, Any]]
    previous_response_id: str | None
    next_input: list[dict[str, Any]]
    pending_tool_outputs: list[dict[str, Any]]
    pending_calls: list[Any]
    steps: list[AgentStep]
    final_answer: str
    stopped_reason: str | None
    iteration: int


class LangGraphAgentLoop:
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
        graph = self._compile_graph(router)

        final_state = await graph.ainvoke(
            LangGraphAgentState(
                question=question,
                model=self._model,
                max_iterations=self._max_iterations,
                available_tools=openai_tools,
                previous_response_id=None,
                next_input=_initial_input(question),
                pending_tool_outputs=[],
                pending_calls=[],
                steps=[],
                final_answer="",
                stopped_reason=None,
                iteration=0,
            )
        )

        return AgentLoopTrace(
            question=question,
            model=self._model,
            max_iterations=self._max_iterations,
            available_tools=openai_tools,
            steps=final_state["steps"],
            final_answer=final_state["final_answer"],
            stopped_reason=final_state["stopped_reason"] or "unknown",
        )

    def _compile_graph(self, router: MCPToolRouter):
        builder = StateGraph(LangGraphAgentState)

        async def model_node(state: LangGraphAgentState) -> dict[str, Any]:
            kwargs: dict[str, Any] = {
                "model": state["model"],
                "input": state["next_input"],
                "tools": state["available_tools"],
                "tool_choice": "auto",
            }
            if state["previous_response_id"] is not None:
                kwargs["previous_response_id"] = state["previous_response_id"]

            response = self._client.responses.create(**kwargs)
            calls = _function_calls(response)
            iteration = state["iteration"] + 1

            if not calls:
                return {
                    "previous_response_id": response.id,
                    "pending_calls": [],
                    "final_answer": getattr(response, "output_text", "") or "",
                    "stopped_reason": "final_answer",
                    "iteration": iteration,
                }

            if len(calls) > self._max_tool_calls_per_iteration:
                return {
                    "previous_response_id": response.id,
                    "pending_calls": [],
                    "final_answer": (
                        f"Model requested {len(calls)} tool calls in iteration {iteration}; "
                        f"this demo allows {self._max_tool_calls_per_iteration}."
                    ),
                    "stopped_reason": "too_many_tool_calls",
                    "iteration": iteration,
                }

            return {
                "previous_response_id": response.id,
                "pending_calls": calls,
                "iteration": iteration,
            }

        async def tools_node(state: LangGraphAgentState) -> dict[str, Any]:
            outputs: list[dict[str, Any]] = []
            steps = list(state["steps"])

            for call in state["pending_calls"]:
                try:
                    arguments = _parse_arguments(call.arguments)
                    route = router.route_for(call.name)
                    mcp_result = await router.call_openai_tool(call.name, arguments)
                except Exception as exc:
                    return {
                        "pending_calls": [],
                        "final_answer": str(exc),
                        "stopped_reason": "tool_request_error",
                    }

                steps.append(
                    AgentStep(
                        iteration=state["iteration"],
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

            return {
                "pending_calls": [],
                "pending_tool_outputs": outputs,
                "next_input": outputs,
                "steps": steps,
            }

        async def synthesize_node(state: LangGraphAgentState) -> dict[str, Any]:
            if state["previous_response_id"] is None or not state["pending_tool_outputs"]:
                return {
                    "final_answer": (
                        f"Stopped after {state['max_iterations']} iterations before "
                        "any tool result was available."
                    ),
                    "stopped_reason": "max_iterations",
                }

            synthesis_input = list(state["pending_tool_outputs"])
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
                model=state["model"],
                previous_response_id=state["previous_response_id"],
                input=synthesis_input,
            )
            final_answer = getattr(response, "output_text", "") or (
                f"Stopped after {state['max_iterations']} iterations. "
                f"The loop collected {len(state['pending_tool_outputs'])} final "
                f"tool observation(s) for: {state['question']}"
            )
            return {
                "final_answer": final_answer,
                "stopped_reason": "max_iterations",
            }

        def route_after_model(state: LangGraphAgentState) -> Literal["tools", "__end__"]:
            if state["stopped_reason"] is not None:
                return "__end__"
            if state["pending_calls"]:
                return "tools"
            return "__end__"

        def route_after_tools(state: LangGraphAgentState) -> Literal["model", "synthesize", "__end__"]:
            if state["stopped_reason"] is not None:
                return "__end__"
            if state["iteration"] >= state["max_iterations"]:
                return "synthesize"
            return "model"

        builder.add_node("model", model_node)
        builder.add_node("tools", tools_node)
        builder.add_node("synthesize", synthesize_node)
        builder.add_edge(START, "model")
        builder.add_conditional_edges(
            "model",
            route_after_model,
            {"tools": "tools", "__end__": END},
        )
        builder.add_conditional_edges(
            "tools",
            route_after_tools,
            {"model": "model", "synthesize": "synthesize", "__end__": END},
        )
        builder.add_edge("synthesize", END)
        return builder.compile()


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
