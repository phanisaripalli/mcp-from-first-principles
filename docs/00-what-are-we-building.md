# 00 - What Are We Building?

We are building a small global-trade intelligence project that can answer evidence-based questions from public data.

The target question is:

> How dependent is Germany on China for lithium-ion battery imports, how concentrated is that supply, and which exporter countries could plausibly serve as alternatives?

That question sounds like something an AI assistant can answer, but it should not invent the statistics from memory. Trade values, country definitions, product classifications, and indicator values change over time. A useful assistant needs to retrieve data, preserve where it came from, and show enough of its work for a reader to inspect the answer.

## Why Start Without MCP?

MCP is an interoperability layer. It helps an AI application discover and call external capabilities in a standard way.

But the first problem is not the protocol. The first problem is getting trustworthy data into a shape that is small, typed, and useful.

So Milestone 1 starts with ordinary Python:

- call the World Bank Indicators API
- normalize the response
- attach provenance
- test the behavior

Once that exists, MCP has something real to expose.

## What Counts As Grounded?

An answer is grounded when it is based on retrieved source data rather than model memory alone.

For this project, every data-bearing result should keep:

- the source API
- the endpoint
- the query parameters
- the retrieval time
- relevant source notes
- pagination metadata when available

This is not paperwork. It is how a reader can ask, "Where did that number come from?"

## Current Boundary

This milestone uses World Bank development indicators only. Trade data, product classification, MCP servers, and agent loops come later.

That boundary keeps the first lesson clean: before tools, servers, and agents, there is just ordinary software that fetches data carefully.

