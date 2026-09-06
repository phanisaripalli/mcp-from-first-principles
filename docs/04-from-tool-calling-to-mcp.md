# 04 - From Tool Calling To MCP

Milestone 2 showed that an LLM-callable tool is not mystical. It is a named capability with a description, an input schema, validation, execution, and a structured result.

So why add MCP?

Because tool calling inside one application is not the same as exposing capabilities through a standard protocol boundary.

## Before MCP

In Milestone 2, the application owned the whole tool integration:

```text
demo/app code
  |
  v
local ToolRegistry
  |
  v
existing WorldBankClient
  |
  v
World Bank API
```

That is useful, but it is application-specific. Another AI host would not automatically know how to discover those tools, what schema dialect they use, how to call them, or how results come back.

## After MCP

Milestone 3 introduces an MCP server as a thin adapter:

```text
MCP host / MCP client
  |
  | MCP
  v
World Bank MCP server
  |
  v
existing WorldBankClient
  |
  v
World Bank API
```

The World Bank client remains the source of truth. The MCP server does not know how World Bank URLs are built or how raw API payloads are normalized. It exposes selected capabilities that already exist.

## Host, Client, Server

Plainly:

- the host is the AI application the user interacts with
- the MCP client is the component inside or beside the host that speaks MCP
- the MCP server is the program exposing capabilities

The model is not the MCP client. The server is not the model. MCP is the protocol boundary between the application side and the capability side.

## Discovery

In Milestone 2, our local registry exposed tool definitions in a shape we invented.

In MCP, discovery is standardized. A client asks the server for tools, and the server returns names, descriptions, and input schemas in the MCP format.

Conceptually:

```json
{
  "method": "tools/list"
}
```

The result is a tool catalog the host can include in model context.

## Invocation

In Milestone 2, our local registry accepted:

```json
{
  "tool": "get_country_profile",
  "arguments": {
    "country": "DEU"
  }
}
```

In MCP, invocation is standardized:

```json
{
  "method": "tools/call",
  "params": {
    "name": "get_country_profile",
    "arguments": {
      "country": "DEU"
    }
  }
}
```

The idea is the same. The boundary is now interoperable.

Tool errors are also part of the boundary. A validation problem inside a tool should be returned as a tool result the model can read and potentially correct. It should not masquerade as a broken protocol connection.

## Transport

Transport is how MCP messages move between client and server.

For local development, `stdio` is common: the host starts the server as a subprocess and talks over standard input/output.

For deployed servers, Streamable HTTP is the modern HTTP transport.

The transport changes how bytes move. It does not change what the World Bank capability is.

## What MCP Standardizes

MCP standardizes:

- how clients discover capabilities
- how tool schemas are represented
- how clients invoke tools
- how servers return tool results
- how tool-level errors are surfaced
- how different hosts and servers can interoperate
- how the protocol boundary is shaped across transports

## What MCP Does Not Do

MCP does not:

- make the model smarter
- decide which tool the model should call
- replace validation, error handling, testing, or provenance
- make bad tool descriptions good
- turn a data client into an agent
- require LangGraph or Google ADK
- require a database or Docker

The host and model decide whether to use a tool. MCP gives them a standard way to discover and call that tool.

## Buzzword Check

What changed:

- the World Bank capabilities are now exposed through an MCP server
- a real MCP client can discover tools with `tools/list`
- a real MCP client can invoke tools with `tools/call`
- schemas and results cross a protocol boundary

What did not change:

- the World Bank API client
- the dataclass domain models
- provenance
- tests for API normalization
- the need for clear tool descriptions
- the need for ordinary software engineering

MCP is the adapter layer. The useful code underneath is still just code.
