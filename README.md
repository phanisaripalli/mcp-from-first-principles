# MCP From First Principles

MCP is useful, but the core idea is less mysterious than the hype can make it sound.

This repository builds a global-trade research assistant one abstraction at a time:

ordinary Python -> tools -> MCP -> multiple servers -> agent loop -> provenance/evaluation

The goal is not to build another toy weather server. It is to show where MCP helps, where ordinary software engineering still does the heavy lifting, and which problems MCP does not solve.

## Current Milestone

Milestone 1 starts with ordinary Python access to World Bank development indicators. There is no MCP server yet.

That is intentional. Before exposing a function as a tool, we want the function itself to be clear, typed, tested, and honest about where its data came from.

## What Works Now

- Look up World Bank country profiles.
- Search World Bank indicator metadata.
- Retrieve indicator observations for one or more countries over a year range.
- Normalize upstream API responses into typed dataclasses.
- Attach provenance metadata to returned data.
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
├── provenance.py
└── worldbank/
    ├── client.py
    ├── errors.py
    └── models.py
```

The World Bank code is deliberately plain. Later milestones can wrap these functions with MCP, but the data access layer should not need to know that MCP exists.

## Official References

- [Model Context Protocol Python SDK](https://py.sdk.modelcontextprotocol.io/)
- [Model Context Protocol specification](https://modelcontextprotocol.io/specification)
- [World Bank Indicators API documentation](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392)
- [World Bank basic API calls](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures)
- [World Bank indicator queries](https://datahelpdesk.worldbank.org/knowledgebase/articles/898599-indicator-api-queries)
- [World Bank country queries](https://datahelpdesk.worldbank.org/knowledgebase/articles/898590-country-api-queries)

## Roadmap

1. Ordinary Python access to World Bank data.
2. Ordinary Python access to trade data.
3. Turn useful functions into MCP tools.
4. Add MCP resources for stable reference data.
5. Split into semantic Trade and Economy MCP servers.
6. Build a plain Python agent loop.
7. Rebuild the same workflow with LangGraph and Google ADK for comparison.

Each step should make the next abstraction feel necessary rather than decorative.

