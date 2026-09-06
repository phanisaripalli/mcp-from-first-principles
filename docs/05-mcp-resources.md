# 05 - MCP Resources

MCP tools let a client ask a server to perform a capability.

MCP resources let a client read addressable context from a server.

That sounds simple, but the distinction is worth slowing down for. Resources are not just "tools that do not take arguments." Resource templates can have URI parameters. The deeper question is whether the interface should feel like an action or like reading a named piece of context.

## The Resource In This Milestone

The World Bank MCP server now exposes one concrete country profile resource:

```text
worldbank://countries/DEU
```

It also exposes one country profile resource template:

```text
worldbank://countries/{country}
```

So a deterministic MCP client can read:

```text
worldbank://countries/IND
```

and receive normalized country metadata as JSON.

## Why A Country Profile Works As A Resource

A country profile is a small reference object. The URI names what the client wants to read:

```text
worldbank://countries/DEU
```

That reads naturally as:

> Give me the World Bank country profile for Germany.

The resource is backed by the same domain function as the `get_country_profile` tool. That is fine. MCP tools and resources can share implementation. The distinction is the interface exposed to the client.

## Tool vs Resource

Tool:

```text
client asks the server to perform a capability
```

Example:

```json
{
  "name": "search_development_indicators",
  "arguments": {
    "query": "gdp",
    "limit": 10
  }
}
```

Resource:

```text
client reads addressable context exposed by the server
```

Example:

```text
worldbank://countries/DEU
```

## Why Indicator Search Remains A Tool

`search_development_indicators` remains a tool because search is an operation. The caller supplies a query, the server performs a lookup over a changing collection, and the result depends on the search behavior.

That is different from reading a country profile by URI.

## Where The Distinction Gets Blurry

Real applications are not always tidy.

The same World Bank country profile can be exposed as:

- a tool: `get_country_profile(country="DEU")`
- a resource: `worldbank://countries/DEU`

Both can call the same Python function. The choice is about the public contract:

- use a tool when the model should choose and execute a capability
- use a resource when the host/client should read named context

In practice, hosts may surface resources in pickers, sidebars, context panels, or retrieval flows. Tools are usually presented to the model as callable actions.

## What Changed

Milestone 4 adds:

- one concrete resource: `worldbank://countries/DEU`
- one resource template: `worldbank://countries/{country}`
- deterministic client code that lists resources
- deterministic client code that reads a resource by URI

## What Did Not Change

The World Bank API client did not change.

The MCP server still stays thin. It exposes a new protocol surface, but the source of truth remains the existing domain layer.

There is still no LLM, no agent loop, no LangGraph, no Google ADK, no database, and no second MCP server.

