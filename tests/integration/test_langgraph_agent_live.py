from __future__ import annotations

import asyncio
import os

import pytest
from dotenv import load_dotenv

from trade_intel.llm.langgraph_agent import LangGraphAgentLoop
from trade_intel.llm.openai_host import default_model_from_env
from trade_intel.mcp.trade_server import create_trade_mcp_server
from trade_intel.mcp.worldbank_server import create_worldbank_mcp_server


pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_LANGGRAPH_AGENT_TESTS") != "1",
    reason="Set RUN_LIVE_LANGGRAPH_AGENT_TESTS=1 to call the live OpenAI API.",
)
def test_live_langgraph_agent_uses_both_mcp_servers() -> None:
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is not set")

    async def scenario():
        agent = LangGraphAgentLoop(
            servers={
                "worldbank": create_worldbank_mcp_server(),
                "trade": create_trade_mcp_server(),
            },
            model=default_model_from_env(),
            max_iterations=5,
        )
        return await agent.answer(
            "How much did Germany import of lithium-ion batteries from China in 2023, "
            "and how large is that trade compared with Germany's 2023 GDP?"
        )

    trace = asyncio.run(scenario())

    assert trace.stopped_reason in {"final_answer", "max_iterations"}
    assert {"trade", "worldbank"}.issubset({step.selected_server for step in trace.steps})
    assert trace.final_answer
