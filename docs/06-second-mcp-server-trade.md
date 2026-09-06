# 06 - A Second MCP Server: Trade Intelligence

Milestone 5 adds a second MCP server.

The teaching question is:

> How do we add a second domain-specific MCP server without coupling it to the World Bank MCP server?

The answer is: keep the domain boundary separate from the protocol boundary.

## Two Independent Domains

The World Bank server owns economy and development-indicator context.

The Trade server owns product codes and trade-flow data.

They both speak MCP, but they do not call each other:

```text
World Bank API
  |
  v
World Bank domain layer
  |
  v
World Bank MCP server
```

```text
UN Comtrade API
  |
  v
Trade domain layer
  |
  v
Trade MCP server
```

The shared protocol is MCP. The domain logic stays separate.

## What This Milestone Adds

The Trade domain layer uses UN Comtrade's public preview API and public reference files.

It supports:

- `find_product_code(query, limit=10)`
- `get_imports(importer, hs_code, year, exporter=None)`

The MCP server exposes only those two tools.

That is enough to demonstrate a second server without pretending we have solved the whole trade-intelligence problem.

## Why UN Comtrade?

UN Comtrade is a natural fit because it models the pieces this project needs to teach:

- reporter countries
- partner countries
- import/export flows
- HS product codes
- reporting periods
- trade values

For this milestone, the code uses the no-key public preview endpoint. That keeps the demo runnable without a paid account or secret.

## Free API Limitations

The public preview endpoint is intentionally limited:

- no subscription key required
- capped at 500 records per call
- limited rate
- one period and product per call
- some descriptive fields may be missing in preview rows

For more usage, UN Comtrade offers free API keys through its developer portal. A later milestone can support `COMTRADE_SUBSCRIPTION_KEY`, but this milestone does not require it.

## Product Codes Are Domain Complexity

MCP does not know what "lithium-ion batteries" means.

The Trade domain layer has to search HS reference data and return candidates. For the demo query, current UN Comtrade HS reference data includes:

```text
850760 - Electric accumulators; lithium-ion, including separators, whether or not rectangular (including square)
```

The tool returns candidates rather than silently guessing. That is ordinary domain design, not protocol magic.

## Imports Are Domain Complexity Too

UN Comtrade identifies countries with numeric M49-style reporter and partner codes. The client accepts ISO3 codes such as `DEU` and `CHN`, then resolves those to Comtrade codes using reference data.

Preview trade rows can be more granular than a single country/product/year value. This milestone requests `breakdownMode=classic` so the preview endpoint returns the classic aggregate view for the requested reporter, partner, product, year, and flow. The client still records response metadata so readers can inspect what happened.

That is a teaching choice, not a claim that preview data is production-grade.

## MCP Complexity != Domain Complexity

MCP standardizes discovery and invocation:

- What tools does this server expose?
- What schemas do those tools have?
- How does a client call them?
- How are results returned?

MCP does not solve:

- HS classification ambiguity
- country-code mapping
- incomplete or revised years
- bilateral asymmetries
- public API limits
- provenance and caveat design
- deciding which domain deserves its own server

Those are still software and data-engineering problems.

## Demo Shape

The deterministic demo:

1. creates an in-memory MCP client/server connection
2. lists Trade MCP tools
3. calls `find_product_code` for lithium-ion batteries
4. uses the first returned HS code
5. calls `get_imports` for Germany imports from China
6. prints structured trade data and provenance
7. exits cleanly

No LLM is involved yet.
