# MCP From First Principles

MCP is useful, but the core idea is less mysterious than the hype can make it sound.

This repository builds a global-trade research assistant one abstraction at a time:

ordinary Python -> tools -> MCP -> multiple servers -> agent loop -> provenance/evaluation

The goal is not to build another toy weather server. It is to show where MCP helps, where ordinary software engineering still does the heavy lifting, and which problems MCP does not solve.

## Current Milestone

Milestone 7 introduces a plain Python agent loop.

The model can now choose a tool, observe the result, and decide whether to call another tool or produce a final answer. The loop is owned by the host/application, not MCP.

## What Works Now

- Look up World Bank country profiles.
- Search World Bank indicator metadata.
- Retrieve indicator observations for one or more countries over a year range.
- Normalize upstream API responses into typed dataclasses.
- Attach provenance metadata to returned data.
- List local tool definitions with names, descriptions, and input schemas.
- Execute structured tool calls against the existing World Bank client.
- Expose World Bank capabilities through a thin MCP server.
- Test MCP tool discovery and invocation without an LLM.
- Expose a small World Bank country profile resource through MCP.
- Read `worldbank://countries/{country}` through a deterministic MCP client.
- Search UN Comtrade HS product codes.
- Retrieve a small normalized import-flow result from UN Comtrade public preview data.
- Expose those trade capabilities through a second independent MCP server.
- Let an OpenAI model choose one MCP-exposed tool for a natural-language question.
- Print the selected tool, arguments, MCP result, and final answer.
- Run a bounded plain-Python agent loop over both MCP servers.
- Print each model decision and MCP observation in the loop.
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

To see MCP tool and resource discovery without an LLM:

```bash
python examples/mcp_worldbank_demo.py IND
```

That demo shows tool discovery, resource discovery, resource-template discovery, resource reading, and tool invocation.

To see the independent Trade MCP server:

```bash
python examples/mcp_trade_demo.py DEU 2023 CHN
```

The demo resolves lithium-ion batteries to an HS code, then queries Germany's imports from China for that product using UN Comtrade public preview data.

To let an OpenAI model choose from both MCP servers:

```bash
python examples/llm_tool_caller_demo.py "What was Germany's nominal GDP in current US dollars in 2023?"
```

or:

```bash
python examples/llm_tool_caller_demo.py "How much did Germany import of lithium-ion batteries from China?"
```

This requires `OPENAI_API_KEY` and may incur OpenAI API cost. Set `OPENAI_MODEL` to choose the model; the default in `.env.example` is `gpt-5-nano`.

To run the first plain-Python agent loop:

```bash
python examples/agent_loop_demo.py
```

The default question asks about Germany's lithium-ion battery imports from China and compares that trade value with Germany's GDP. The demo prints each selected MCP tool, its arguments, each observation, and the final answer.

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

To call the live UN Comtrade public preview API:

```bash
RUN_LIVE_COMTRADE_TESTS=1 pytest tests/integration/test_comtrade_live.py
```

To call the live OpenAI API, which may incur cost:

```bash
RUN_LIVE_OPENAI_TESTS=1 pytest tests/integration/test_openai_live.py
```

To call the live OpenAI API through the bounded agent loop:

```bash
RUN_LIVE_OPENAI_AGENT_TESTS=1 pytest tests/integration/test_openai_agent_live.py
```

For more Comtrade usage, create a free key through the [UN Comtrade Developer Portal](https://comtradedeveloper.un.org/), subscribe to **Free APIs**, then find the key in your developer profile. A later milestone can support `COMTRADE_SUBSCRIPTION_KEY`; the current Trade demo does not require it.

## Project Structure

```text
src/trade_intel/
├── mcp/
│   ├── trade_server.py
│   └── worldbank_server.py
├── llm/
│   ├── agent_loop.py
│   ├── openai_host.py
│   ├── routing.py
│   └── tool_adapter.py
├── provenance.py
├── trade/
│   ├── client.py
│   ├── errors.py
│   ├── models.py
│   └── reference.py
├── tools/
│   ├── registry.py
│   ├── schemas.py
│   └── worldbank_tools.py
└── worldbank/
    ├── client.py
    ├── errors.py
    └── models.py
```

The World Bank and Trade code are deliberately plain. MCP servers wrap those domain layers without duplicating API logic. The data access layers do not need to know that MCP exists.

## Official References

- [Model Context Protocol Python SDK](https://py.sdk.modelcontextprotocol.io/)
- [Model Context Protocol specification](https://modelcontextprotocol.io/specification)
- [World Bank Indicators API documentation](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392)
- [World Bank basic API calls](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures)
- [World Bank indicator queries](https://datahelpdesk.worldbank.org/knowledgebase/articles/898599-indicator-api-queries)
- [World Bank country queries](https://datahelpdesk.worldbank.org/knowledgebase/articles/898590-country-api-queries)
- [UN Comtrade API documentation](https://uncomtrade.org/docs/un-comtrade-api/)
- [UN Comtrade API subscription keys](https://uncomtrade.org/docs/api-subscription-keys/)
- [UN Comtrade country codes](https://uncomtrade.org/docs/country-codes/)

## Roadmap

1. Ordinary Python access to World Bank data.
2. Wrap ordinary Python functions as local LLM-callable tools.
3. Expose selected tools through MCP.
4. Add a small MCP resource for addressable World Bank context.
5. Add a second independent MCP server for trade data.
6. Let an LLM choose one MCP-exposed tool.
7. Build a bounded plain-Python agent loop.
8. Add MCP resources for stable trade reference data.
9. Compose Trade and Economy capabilities from a host.
10. Rebuild the same workflow with LangGraph and Google ADK for comparison.

Each step should make the next abstraction feel necessary rather than decorative.
