# 01 - Ordinary Python World Bank Access

Milestone 1 implements a small typed client for the World Bank Indicators API V2.

There is no MCP in this milestone. The code is normal Python because that is the baseline we want readers to understand before adding protocol machinery.

## Capabilities

The client exposes three operations:

- `search_indicators(query, limit=10)`
- `get_indicator(countries, indicator, start_year, end_year)`
- `get_country_profile(country)`

These are domain-level operations, not one-to-one mirrors of every upstream endpoint.

## Why Normalize?

Public APIs often return payloads shaped for broad compatibility rather than for our exact use case. The World Bank API returns collection responses with metadata plus a list of rows.

The project normalizes those rows into dataclasses:

- `IndicatorSummary`
- `IndicatorObservation`
- `CountryProfile`

This keeps the rest of the project from depending on raw upstream response details.

## Why Provenance?

A value without source context is hard to trust. Each normalized result includes a `Provenance` object with source, endpoint, query parameters, retrieval time, and available paging metadata.

Later, when an AI assistant summarizes findings, it can point back to the data it actually used.

## Why Async?

The client uses async HTTP because later milestones will need multiple independent data calls. Async gives us that option without changing the public shape of the data models.

There is still no agent loop here. A Python function calling an API is just a Python function calling an API.

## Test Strategy

Unit tests use mocked HTTP responses so they are deterministic and fast. Live World Bank tests are opt-in because public API availability should not be required for every local test run.

