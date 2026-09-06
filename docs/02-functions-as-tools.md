# 02 - Functions As Tools

Milestone 1 gave us ordinary Python functions that can fetch World Bank data.

Milestone 2 asks a smaller question than MCP:

> What has to change for an LLM to use an ordinary Python function as a tool?

The answer is: not as much as the jargon makes it sound.

## Ordinary Function

A normal Python caller already knows which function it wants:

```python
profile = await client.get_country_profile("DEU")
```

The caller is a programmer. The programmer read the code and passed the right argument.

## LLM-Callable Tool

An LLM-callable tool needs a little more public information:

- name
- description
- input schema
- validation
- execution path
- structured result

The model does not inspect the source code. It sees a tool description and decides whether that tool is relevant.

For this project, the same operation becomes a structured request:

```json
{
  "tool": "get_country_profile",
  "arguments": {
    "country": "DEU"
  }
}
```

The tool layer validates the arguments, calls the existing World Bank client, and returns structured content.

## What The Tool Layer Does

The tool layer in this milestone is deliberately small:

1. Store tool definitions in a registry.
2. Publish each tool's name, description, and input schema.
3. Accept a tool name and argument object.
4. Reject missing, extra, or wrongly typed arguments.
5. Execute the existing domain function.
6. Convert dataclass results into structured data.

There is no MCP yet. There is no model loop yet. We are isolating the concept of tool calling before adding a protocol.

## Why Not Put API Logic In Tools?

The World Bank client already knows how to call the API, parse responses, and attach provenance.

The tool layer should not duplicate that logic. Its job is the boundary between a probabilistic caller and deterministic code.

That keeps the architecture honest:

```text
tool registry -> existing WorldBankClient -> World Bank API
```

Later, MCP can standardize this boundary. It should not force us to rewrite the domain layer.

