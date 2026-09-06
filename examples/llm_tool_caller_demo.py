from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import asdict

from dotenv import load_dotenv

from trade_intel.llm.openai_host import OpenAIMCPHost, default_model_from_env
from trade_intel.mcp.trade_server import create_trade_mcp_server
from trade_intel.mcp.worldbank_server import create_worldbank_mcp_server


DEFAULT_QUESTION = "How much did Germany import of lithium-ion batteries from China?"


def question_from_args(args: list[str]) -> str:
    if not args:
        return DEFAULT_QUESTION
    return " ".join(args).strip()


async def main(question: str) -> None:
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in the environment or .env before running this demo.")

    host = OpenAIMCPHost(
        servers={
            "worldbank": create_worldbank_mcp_server(),
            "trade": create_trade_mcp_server(),
        },
        model=default_model_from_env(),
    )
    trace = await host.answer(question)

    print(f"User question:\n{trace.question}")
    print(f"\nModel:\n{trace.model}")
    print(f"\nModel selected:\n{trace.selected_tool or '(no tool)'}")
    print("\nArguments:")
    print(json.dumps(trace.arguments, indent=2, default=str))
    print("\nMCP result:")
    print(json.dumps(trace.mcp_result, indent=2, default=str))
    print("\nFinal answer:")
    print(trace.final_answer)

    print("\nFull trace:")
    print(json.dumps(asdict(trace), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main(question_from_args(sys.argv[1:])))

