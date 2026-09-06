from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict

from trade_intel.tools.worldbank_tools import (
    build_worldbank_tool_registry,
    poor_worldbank_tool_schema,
)
from trade_intel.worldbank import WorldBankClient


def country_from_args(args: list[str]) -> str:
    if not args:
        return "DEU"
    if len(args) > 1:
        raise ValueError("Usage: python examples/tool_calling_demo.py [COUNTRY_CODE]")
    return args[0].strip().upper()


async def main(country: str = "DEU") -> None:
    async with WorldBankClient() as client:
        registry = build_worldbank_tool_registry(client)

        print("Poor generic tool interface:")
        print(json.dumps(poor_worldbank_tool_schema(), indent=2, default=str))

        print("\nDomain-specific tool interfaces:")
        print(json.dumps(registry.list_tools(), indent=2, default=str))

        print("\nStructured tool call:")
        result = await registry.call_tool("get_country_profile", {"country": country})
        print(json.dumps(asdict(result), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main(country_from_args(sys.argv[1:])))
