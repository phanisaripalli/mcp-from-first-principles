# 07 - An LLM As The MCP Tool Caller

Milestone 6 introduces an LLM for the first time.

The teaching question is:

> What changes when the caller is a language model rather than deterministic code?

The answer is that the tool-selection boundary moves.

## Before: Deterministic Caller

In Milestone 5, the demo code chose the server and tool explicitly:

```text
deterministic Python code
  |
  v
Trade MCP / get_imports
  |
  v
UN Comtrade domain layer
```

There was no ambiguity. The Python script already knew which tool to call.

## Now: Model-Selected Tool

In Milestone 6, the model sees available tool names, descriptions, and schemas, then asks for one tool call:

```text
User question
  |
  v
OpenAI model
  |
  v
model selects a tool and arguments
  |
  v
host routes the call to MCP
  |
  +--> World Bank MCP server
  |
  +--> Trade MCP server
```

The servers do not know whether the caller was deterministic Python or an LLM. They still receive MCP calls and execute ordinary domain code.

## MCP Does Not Choose

MCP exposes capabilities. It does not decide which capability is relevant.

The model chooses based on:

- tool name
- tool description
- input schema
- the user's question
- the instructions supplied by the host

The host executes the chosen tool through MCP.

## Why Translate Tool Schemas?

The MCP servers expose MCP tool schemas.

The OpenAI Responses API expects OpenAI function tools.

So the host performs a small translation:

```text
MCP tool
  name: get_imports
  schema: ...

OpenAI function tool
  name: trade__get_imports
  parameters: ...
```

The prefix keeps names unique because OpenAI sees one flat list of tools, while the host still knows which MCP server owns each tool.

## Why One Tool Call?

This is not a general agent framework yet.

The demo supports one model-selected tool call:

1. user asks a question
2. model selects one tool and arguments
3. host executes that tool through MCP
4. host returns the result to the model
5. model writes the final answer

If the model asks for more than one tool call, the host reports that the milestone only supports one. That constraint keeps the lesson small.

## What Changed

- An OpenAI model now chooses a tool from MCP-discovered schemas.
- The host translates MCP tool schemas into OpenAI function tools.
- The host routes prefixed OpenAI tool names back to MCP server/tool pairs.
- The World Bank MCP server now exposes the existing `get_development_indicator` domain capability so the GDP demo can be answered with one tool call.
- The demo prints the selected tool, arguments, MCP result, and final answer.

## What Did Not Change

- World Bank domain logic did not change.
- Trade domain logic did not change.
- The MCP servers did not start calling each other.
- MCP did not become an agent framework.
- There is still no LangGraph, Google ADK, memory, database, or autonomous planning loop.

The model is now the tool selector. The host is still the executor. MCP is still the protocol boundary.
