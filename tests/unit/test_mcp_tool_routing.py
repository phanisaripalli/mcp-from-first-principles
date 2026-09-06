from __future__ import annotations

import asyncio
import json

import httpx

from trade_intel.llm.tool_adapter import discover_openai_tools
from trade_intel.mcp.trade_server import create_trade_mcp_server
from trade_intel.trade import TradeClient


def run(coro):
    return asyncio.run(coro)


def make_transport(payloads: dict[str, object]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.url.path}?{request.url.query.decode()}"
        return httpx.Response(200, content=json.dumps(payloads[key]).encode("utf-8"))

    return httpx.MockTransport(handler)


def test_routes_prefixed_openai_tool_name_back_to_mcp_tool() -> None:
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

    async def scenario():
        _specs, router = await discover_openai_tools(
            {"trade": create_trade_mcp_server(client_factory)}
        )
        return await router.call_openai_tool(
            "trade__find_product_code",
            {"query": "lithium-ion batteries", "limit": 5},
        )

    result = run(scenario())

    assert result["server_label"] == "trade"
    assert result["mcp_tool"] == "find_product_code"
    assert result["is_error"] is False
    assert result["structured_content"]["candidates"][0]["hs_code"] == "850760"

