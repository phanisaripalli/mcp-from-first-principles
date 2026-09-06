from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

import httpx

from trade_intel.llm.openai_host import OpenAIMCPHost
from trade_intel.mcp.trade_server import create_trade_mcp_server
from trade_intel.trade import TradeClient


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


class FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> FakeResponse:
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return FakeResponse(
                id="response-1",
                output=[
                    FakeFunctionCall(
                        type="function_call",
                        name="trade__find_product_code",
                        arguments=json.dumps({"query": "lithium-ion batteries", "limit": 5}),
                        call_id="call-1",
                    )
                ],
            )
        return FakeResponse(
            id="response-2",
            output=[],
            output_text="HS 850760 is the lithium-ion battery product code.",
        )


class FakeOpenAI:
    def __init__(self) -> None:
        self.responses = FakeResponses()


def make_transport(payloads: dict[str, object]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.url.path}?{request.url.query.decode()}"
        return httpx.Response(200, content=json.dumps(payloads[key]).encode("utf-8"))

    return httpx.MockTransport(handler)


def test_host_allows_model_to_select_one_mcp_tool() -> None:
    payloads = {
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
    }

    def client_factory():
        return TradeClient(transport=make_transport(payloads))

    fake_openai = FakeOpenAI()
    host = OpenAIMCPHost(
        servers={"trade": create_trade_mcp_server(client_factory)},
        model="test-model",
        client=fake_openai,
    )

    trace = run(host.answer("Which HS code is lithium-ion batteries?"))

    assert trace.selected_tool == "trade__find_product_code"
    assert trace.selected_server == "trade"
    assert trace.selected_mcp_tool == "find_product_code"
    assert trace.arguments == {"query": "lithium-ion batteries", "limit": 5}
    assert trace.mcp_result["structured_content"]["candidates"][0]["hs_code"] == "850760"
    assert trace.final_answer == "HS 850760 is the lithium-ion battery product code."
    assert fake_openai.responses.calls[0]["tool_choice"] == "auto"
    assert fake_openai.responses.calls[1]["input"][0]["type"] == "function_call_output"

