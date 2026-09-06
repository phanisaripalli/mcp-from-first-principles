# AGENTS.md

## Project Purpose

This repository is an educational global-trade intelligence lab. It teaches MCP and agentic concepts from first principles by starting with ordinary Python, then adding abstractions only when the code has earned them.

The goal is not to hide simple ideas behind buzzwords. The goal is to show why each layer exists.

## Core Principles

- Start with the real data problem.
- Prefer ordinary Python before protocol or framework code.
- Introduce MCP only after plain functions make the boundary useful.
- Introduce agent loops only after there is a real model -> tool -> observation -> model cycle.
- Introduce LangGraph and Google ADK only after the plain loop exists as a baseline.
- Keep domain clients framework-neutral.
- Preserve provenance for every returned data point.
- Normalize upstream API responses into small typed models.
- Avoid dumping raw API payloads into model context.
- Keep dependencies minimal.
- Prefer simple code over premature abstractions.
- Add tests with each capability.

## Current Constraints

Do not add these until a later milestone explicitly calls for them:

- MCP server code
- LangGraph
- Google ADK
- database storage
- Docker
- background jobs
- broad caching layers
- complex orchestration

## Milestone Rules

Milestone 1 is ordinary Python access to World Bank data. No MCP yet.

Milestone 2 is a minimal local tool-calling layer over the World Bank client. Still no MCP yet.

Milestone 3 introduces MCP for the first time. The MCP server must be a thin adapter over existing capabilities.

Milestone 4 introduces MCP resources. Add resources only when the data is naturally addressable context. Do not create resources merely because MCP supports them.

Milestone 5 introduces a second MCP server for Trade Intelligence. The Trade MCP server must not call the World Bank MCP server. Both servers should remain independent capabilities that happen to speak the same protocol.

Milestone 6 introduces an OpenAI model as the caller. The model may choose a tool, but the host executes that choice through MCP. This is not a general autonomous agent loop.

Milestone 7 introduces a bounded plain-Python agent loop. The loop is the new concept: reason, act, observe, reason again. MCP servers should remain unchanged.

Build only what helps explain:

- ordinary Python function vs LLM-callable tool
- tool name and description
- input schema
- structured arguments
- validation
- tool execution
- structured tool results
- why tool descriptions matter for a probabilistic caller

For Milestone 3, do not move World Bank API/domain logic into the MCP server. The MCP layer exists to demonstrate standardized discovery and invocation across a protocol boundary.

For Milestone 4, keep tools and resources conceptually distinct:

- tools ask the server to perform a capability
- resources let the client read addressable context

It is acceptable for a tool and a resource to reuse the same domain function.

For Milestone 5, keep the architecture layered:

- Trade API
- typed Trade client/domain functions
- Trade MCP server
- deterministic MCP client/demo

MCP does not solve product classification, country-code mapping, missing data, revisions, or API limitations. Document those as ordinary software/data-engineering problems.

For Milestone 6:

- use the OpenAI Responses API only
- read `OPENAI_API_KEY` and `OPENAI_MODEL` from the environment
- do not print secrets
- derive model tools from MCP discovery where practical
- keep the MCP-to-OpenAI schema adapter small and explicit
- support one model-selected tool-call round only
- do not introduce LangGraph, Google ADK, memory, retries, or planning loops

For Milestone 7:

- keep the loop explicit and readable
- use `max_iterations` and `max_tool_calls_per_iteration`
- record model decisions, MCP routes, arguments, observations, and final answer
- do not build a generic framework
- do not add memory, vector search, retries, planner/executor splits, or multi-agent behavior

## Documentation Style

Write for smart readers who may be new to MCP. Explain concepts plainly. Prefer examples over terminology. When introducing a buzzword, first show the ordinary software problem it solves.

## Data Handling

Every data-bearing result should include enough information to inspect where it came from:

- upstream source
- endpoint or URL
- query parameters
- retrieval timestamp
- relevant source notes
- pagination or response metadata when applicable

## Testing Expectations

Use deterministic unit tests for parsing, validation, and calculations. Live API tests should be optional and easy to skip when network access is unavailable.
