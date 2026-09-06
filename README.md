# MCP From First Principles

MCP is useful, but the core idea is less mysterious than the hype can make it sound.

This repository builds a global-trade research assistant one abstraction at a time:

ordinary Python -> tools -> MCP -> multiple servers -> agent loop -> provenance/evaluation

The goal is not to build another toy weather server. It is to show where MCP helps, where ordinary software engineering still does the heavy lifting, and which problems MCP does not solve.

## Current Milestone

Milestone 3 exposes a small subset of the existing World Bank capabilities through MCP for the first time.

Milestone 2 showed application-specific tool calling. Milestone 3 shows the interoperability step: a host/client can discover and invoke tools through a standard MCP protocol boundary.

## What Works Now

- Look up World Bank country profiles.
- Search World Bank indicator metadata.
- Retrieve indicator observations for one or more countries over a year range.
- Normalize upstream API responses into typed dataclasses.
- Attach provenance metadata to returned data.
- List local tool definitions with names, descriptions, and input schemas.
- Execute structured tool calls against the existing World Bank client.
- Expose two World Bank capabilities through a thin MCP server.
- Test MCP tool discovery and invocation without an LLM.
- Run unit tests without network access.
- Optionally run a live World Bank integration test.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Try It

```bash
python examples/worldbank_smoke.py
```

The example fetches Germany's World Bank country profile and recent GDP observations.

To see the tool-calling concept before MCP:

```bash
python examples/tool_calling_demo.py
```

The demo contrasts a vague generic World Bank query tool with clearer domain-specific tools, then executes `get_country_profile` using structured arguments.

To see MCP discovery and invocation without an LLM:

```bash
python examples/mcp_worldbank_demo.py IND
```

To run the MCP server over stdio for an MCP-capable host:

```bash
python -m trade_intel.mcp.worldbank_server
```

That command waits for an MCP client to speak over standard input/output, so it will appear to hang if you run it directly in a normal terminal.

## Run Tests

```bash
pytest
```

Live API tests are skipped by default:

```bash
RUN_LIVE_WORLD_BANK_TESTS=1 pytest tests/integration
```

## Project Structure

```text
src/trade_intel/
├── mcp/
│   └── worldbank_server.py
├── provenance.py
├── tools/
│   ├── registry.py
│   ├── schemas.py
│   └── worldbank_tools.py
└── worldbank/
    ├── client.py
    ├── errors.py
    └── models.py
```

The World Bank code is deliberately plain. The local tool layer and MCP server both wrap these functions without duplicating API logic. The data access layer does not need to know that MCP exists.

## Official References

- [Model Context Protocol Python SDK](https://py.sdk.modelcontextprotocol.io/)
- [Model Context Protocol specification](https://modelcontextprotocol.io/specification)
- [World Bank Indicators API documentation](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392)
- [World Bank basic API calls](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures)
- [World Bank indicator queries](https://datahelpdesk.worldbank.org/knowledgebase/articles/898599-indicator-api-queries)
- [World Bank country queries](https://datahelpdesk.worldbank.org/knowledgebase/articles/898590-country-api-queries)

## Roadmap

1. Ordinary Python access to World Bank data.
2. Wrap ordinary Python functions as local LLM-callable tools.
3. Expose selected tools through MCP.
4. Ordinary Python access to trade data.
5. Add MCP resources for stable reference data.
6. Split into semantic Trade and Economy MCP servers.
7. Build a plain Python agent loop.
8. Rebuild the same workflow with LangGraph and Google ADK for comparison.

Each step should make the next abstraction feel necessary rather than decorative.
