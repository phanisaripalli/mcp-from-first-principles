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
