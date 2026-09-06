from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any

from dotenv import load_dotenv

from trade_intel.llm.langgraph_agent import LangGraphAgentLoop
from trade_intel.llm.openai_host import default_model_from_env
from trade_intel.mcp.trade_server import create_trade_mcp_server
from trade_intel.mcp.worldbank_server import create_worldbank_mcp_server


DEFAULT_QUESTION = (
    "How much did Germany import of lithium-ion batteries from China in 2023, "
    "and how large is that trade compared with Germany's 2023 GDP?"
)


def question_from_args(args: list[str]) -> str:
    if not args:
        return DEFAULT_QUESTION
    return " ".join(args).strip()


def observation_summary(mcp_result: dict[str, Any]) -> dict[str, Any]:
    structured = mcp_result.get("structured_content")
    if not isinstance(structured, dict):
        return mcp_result

    if "candidates" in structured:
        return {
            "candidates": [
                {
                    "hs_code": candidate.get("hs_code"),
                    "description": candidate.get("description"),
                    "is_leaf": candidate.get("is_leaf"),
                }
                for candidate in structured.get("candidates", [])[:3]
            ],
            "provenance": structured.get("provenance"),
        }

    if "trade_value_usd" in structured:
        return {
            "importer": structured.get("importer_code"),
            "exporter": structured.get("exporter_code"),
            "hs_code": structured.get("hs_code"),
            "year": structured.get("year"),
            "trade_value_usd": structured.get("trade_value_usd"),
            "source": structured.get("source"),
            "provenance": structured.get("provenance"),
        }

    if "observations" in structured:
        return {
            "indicator": structured.get("indicator"),
            "observations": [
                {
                    "country_code": observation.get("country_code"),
                    "indicator_code": observation.get("indicator_code"),
                    "year": observation.get("year"),
                    "value": observation.get("value"),
                    "source": observation.get("source"),
                }
                for observation in structured.get("observations", [])[:3]
            ],
            "provenance": structured.get("provenance"),
        }

    return structured


async def main(question: str) -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("mcp").setLevel(logging.WARNING)
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in the environment or .env before running this demo.")

    agent = LangGraphAgentLoop(
        servers={
            "worldbank": create_worldbank_mcp_server(),
            "trade": create_trade_mcp_server(),
        },
        model=default_model_from_env(),
        max_iterations=5,
    )
    trace = await agent.answer(question)

    print(f"User question:\n{trace.question}")
    print(f"\nModel:\n{trace.model}")
    print(f"\nGraph:\nSTART -> model -> tools -> model, with conditional END")
    print(f"\nMax iterations:\n{trace.max_iterations}")

    if not trace.steps:
        print("\nNo tool calls were made.")
    for step in trace.steps:
        print(f"\nIteration {step.iteration}: model selected")
        print(f"{step.selected_server} MCP / {step.selected_mcp_tool}")
        print("\nArguments:")
        print(json.dumps(step.arguments, indent=2, default=str))
        print("\nObservation:")
        print(json.dumps(observation_summary(step.mcp_result), indent=2, default=str))

    print(f"\nStopped reason:\n{trace.stopped_reason}")
    print("\nFinal answer:")
    print(trace.final_answer)


if __name__ == "__main__":
    asyncio.run(main(question_from_args(sys.argv[1:])))
