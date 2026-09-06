from __future__ import annotations

import asyncio
import os

import pytest
from dotenv import load_dotenv

from trade_intel.llm.openai_host import OpenAIMCPHost, default_model_from_env
from trade_intel.mcp.trade_server import create_trade_mcp_server
from trade_intel.mcp.worldbank_server import create_worldbank_mcp_server


pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_OPENAI_TESTS") != "1",
    reason="Set RUN_LIVE_OPENAI_TESTS=1 to call the live OpenAI API.",
)
def test_live_openai_selects_an_mcp_tool() -> None:
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is not set")

    async def scenario():
        host = OpenAIMCPHost(
            servers={
                "worldbank": create_worldbank_mcp_server(),
                "trade": create_trade_mcp_server(),
            },
            model=default_model_from_env(),
        )
        return await host.answer("What is Germany's GDP?")

    trace = asyncio.run(scenario())

    assert trace.selected_tool is not None
    assert trace.mcp_result is not None
    assert trace.final_answer

