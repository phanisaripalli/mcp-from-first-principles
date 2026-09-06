from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

import httpx

from trade_intel.llm.agent_loop import PlainPythonAgentLoop
from trade_intel.mcp.trade_server import create_trade_mcp_server
from trade_intel.mcp.worldbank_server import create_worldbank_mcp_server
from trade_intel.trade import TradeClient
from trade_intel.worldbank import WorldBankClient


def run(coro):
    return asyncio.run(coro)


@dataclass(frozen=True)
class FakeFunctionCall:
    type: str
    name: str
    arguments: str
    call_id: str


@dataclass(frozen=True)
class FakeResponse:
    id: str
    output: list[Any]
    output_text: str = ""


class ScriptedResponses:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> FakeResponse:
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("No scripted response available")
        return self._responses.pop(0)


class FakeOpenAI:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = ScriptedResponses(responses)


def make_transport(payloads: dict[str, object]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.url.path}?{request.url.query.decode()}"
        payload = payloads.get(key)
        if payload is None:
            return httpx.Response(404, json={"message": f"not found: {key}"})
        return httpx.Response(200, content=json.dumps(payload).encode("utf-8"))

    return httpx.MockTransport(handler)


def trade_payloads() -> dict[str, object]:
    return {
        "/files/v1/app/reference/Reporters.json?": {
            "results": [
                {
                    "reporterCode": 276,
                    "reporterDesc": "Germany",
                    "reporterCodeIsoAlpha3": "DEU",
                }
            ]
        },
        "/files/v1/app/reference/partnerAreas.json?": {
            "results": [
                {
                    "PartnerCode": 156,
                    "PartnerDesc": "China",
                    "PartnerCodeIsoAlpha3": "CHN",
                }
            ]
        },
        "/files/v1/app/reference/HS.json?": {
            "className": "Combined HS",
            "results": [
                {
                    "id": "850760",
                    "text": "850760 - Electric accumulators; lithium-ion",
                    "parent": "8507",
                    "isLeaf": "1",
                    "aggrLevel": 6,
                    "standardUnitAbbr": "u",
                }
            ],
        },
        "/public/v1/preview/C/A/HS?flowCode=M&reporterCode=276&period=2023&cmdCode=850760&partnerCode=156&breakdownMode=classic": {
            "elapsedTime": "0.1 secs",
            "count": 1,
            "data": [{"primaryValue": 100.0}],
        },
    }


def worldbank_payloads() -> dict[str, object]:
    indicator_payload = [
        {"page": 1, "pages": 1, "per_page": "50", "total": 1},
        [
            {
                "id": "NY.GDP.MKTP.CD",
                "name": "GDP (current US$)",
                "unit": "",
                "source": {"id": "2", "value": "World Development Indicators"},
                "sourceNote": "GDP at purchaser's prices.",
                "sourceOrganization": "World Bank national accounts data.",
                "topics": [{"id": "3", "value": "Economy & Growth"}],
            }
        ],
    ]
    return {
        "/v2/indicator/NY.GDP.MKTP.CD?format=json": indicator_payload,
        "/v2/country/deu/indicator/NY.GDP.MKTP.CD?format=json&date=2023%3A2023&per_page=20000": [
            {"page": 1, "pages": 1, "per_page": "20000", "total": 1},
            [
                {
                    "countryiso3code": "DEU",
                    "country": {"id": "DE", "value": "Germany"},
                    "date": "2023",
                    "value": 4562207532490.28,
                }
            ],
        ],
    }


def test_agent_loop_handles_one_tool_call_then_final_answer() -> None:
    fake_openai = FakeOpenAI(
        [
            FakeResponse(
                id="r1",
                output=[
                    FakeFunctionCall(
                        type="function_call",
                        name="trade__find_product_code",
                        arguments=json.dumps({"query": "lithium-ion batteries", "limit": 5}),
                        call_id="call-1",
                    )
                ],
            ),
            FakeResponse(id="r2", output=[], output_text="Use HS 850760."),
        ]
    )

    def trade_client():
        return TradeClient(transport=make_transport(trade_payloads()))

    host = PlainPythonAgentLoop(
        servers={"trade": create_trade_mcp_server(trade_client)},
        model="test-model",
        client=fake_openai,
    )

    trace = run(host.answer("Which HS code is lithium-ion batteries?"))

    assert trace.stopped_reason == "final_answer"
    assert len(trace.steps) == 1
    assert trace.steps[0].selected_tool == "trade__find_product_code"
    assert trace.steps[0].mcp_result["structured_content"]["candidates"][0]["hs_code"] == "850760"
    assert trace.final_answer == "Use HS 850760."
    assert fake_openai.responses.calls[1]["previous_response_id"] == "r1"


def test_agent_loop_handles_multiple_sequential_tool_calls_from_both_servers() -> None:
    fake_openai = FakeOpenAI(
        [
            FakeResponse(
                id="r1",
                output=[
                    FakeFunctionCall(
                        type="function_call",
                        name="trade__find_product_code",
                        arguments=json.dumps({"query": "lithium-ion batteries", "limit": 5}),
                        call_id="call-1",
                    )
                ],
            ),
            FakeResponse(
                id="r2",
                output=[
                    FakeFunctionCall(
                        type="function_call",
                        name="trade__get_imports",
                        arguments=json.dumps(
                            {
                                "importer": "DEU",
                                "hs_code": "850760",
                                "year": 2023,
                                "exporter": "CHN",
                            }
                        ),
                        call_id="call-2",
                    )
                ],
            ),
            FakeResponse(
                id="r3",
                output=[
                    FakeFunctionCall(
                        type="function_call",
                        name="worldbank__get_development_indicator",
                        arguments=json.dumps(
                            {
                                "countries": ["DEU"],
                                "indicator": "NY.GDP.MKTP.CD",
                                "start_year": 2023,
                                "end_year": 2023,
                            }
                        ),
                        call_id="call-3",
                    )
                ],
            ),
            FakeResponse(
                id="r4",
                output=[],
                output_text="Germany imported lithium-ion batteries from China and has GDP context.",
            ),
        ]
    )

    def trade_client():
        return TradeClient(transport=make_transport(trade_payloads()))

    def worldbank_client():
        return WorldBankClient(transport=make_transport(worldbank_payloads()))

    host = PlainPythonAgentLoop(
        servers={
            "trade": create_trade_mcp_server(trade_client),
            "worldbank": create_worldbank_mcp_server(worldbank_client),
        },
        model="test-model",
        client=fake_openai,
        max_iterations=5,
    )

    trace = run(host.answer("Assess Germany battery import dependence with GDP context."))

    assert trace.stopped_reason == "final_answer"
    assert [step.selected_server for step in trace.steps] == ["trade", "trade", "worldbank"]
    assert [step.selected_mcp_tool for step in trace.steps] == [
        "find_product_code",
        "get_imports",
        "get_development_indicator",
    ]
    assert trace.steps[1].mcp_result["structured_content"]["trade_value_usd"] == 100.0
    assert trace.steps[2].mcp_result["structured_content"]["observations"][0]["country_code"] == "DEU"


def test_agent_loop_stops_at_max_iterations() -> None:
    fake_openai = FakeOpenAI(
        [
            FakeResponse(
                id="r1",
                output=[
                    FakeFunctionCall(
                        type="function_call",
                        name="trade__find_product_code",
                        arguments=json.dumps({"query": "lithium-ion batteries", "limit": 5}),
                        call_id="call-1",
                    )
                ],
            ),
            FakeResponse(
                id="r2",
                output=[],
                output_text="Partial answer from the available tool observation.",
            ),
        ]
    )

    def trade_client():
        return TradeClient(transport=make_transport(trade_payloads()))

    host = PlainPythonAgentLoop(
        servers={"trade": create_trade_mcp_server(trade_client)},
        model="test-model",
        client=fake_openai,
        max_iterations=1,
    )

    trace = run(host.answer("Keep searching."))

    assert trace.stopped_reason == "max_iterations"
    assert trace.final_answer == "Partial answer from the available tool observation."
    assert len(fake_openai.responses.calls) == 2
    assert "tools" not in fake_openai.responses.calls[1]
    assert fake_openai.responses.calls[1]["previous_response_id"] == "r1"


def test_agent_loop_stops_on_unknown_tool_request() -> None:
    fake_openai = FakeOpenAI(
        [
            FakeResponse(
                id="r1",
                output=[
                    FakeFunctionCall(
                        type="function_call",
                        name="missing__tool",
                        arguments="{}",
                        call_id="call-1",
                    )
                ],
            )
        ]
    )
    host = PlainPythonAgentLoop(servers={}, model="test-model", client=fake_openai)

    trace = run(host.answer("Call a missing tool."))

    assert trace.stopped_reason == "tool_request_error"
    assert "Unknown OpenAI tool name" in trace.final_answer


def test_agent_loop_stops_on_malformed_arguments() -> None:
    fake_openai = FakeOpenAI(
        [
            FakeResponse(
                id="r1",
                output=[
                    FakeFunctionCall(
                        type="function_call",
                        name="trade__find_product_code",
                        arguments="{not-json",
                        call_id="call-1",
                    )
                ],
            )
        ]
    )
    host = PlainPythonAgentLoop(
        servers={"trade": create_trade_mcp_server()},
        model="test-model",
        client=fake_openai,
    )

    trace = run(host.answer("Use malformed args."))

    assert trace.stopped_reason == "tool_request_error"
    assert "Expecting property name" in trace.final_answer


def test_agent_loop_stops_on_too_many_tool_calls_in_one_iteration() -> None:
    fake_openai = FakeOpenAI(
        [
            FakeResponse(
                id="r1",
                output=[
                    FakeFunctionCall("function_call", "trade__find_product_code", "{}", "call-1"),
                    FakeFunctionCall("function_call", "trade__find_product_code", "{}", "call-2"),
                    FakeFunctionCall("function_call", "trade__find_product_code", "{}", "call-3"),
                ],
            )
        ]
    )
    host = PlainPythonAgentLoop(
        servers={"trade": create_trade_mcp_server()},
        model="test-model",
        client=fake_openai,
        max_tool_calls_per_iteration=2,
    )

    trace = run(host.answer("Call many tools."))

    assert trace.stopped_reason == "too_many_tool_calls"
    assert "Model requested 3 tool calls" in trace.final_answer
