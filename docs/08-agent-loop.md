# 08 - From Tool Calling To An Agent Loop

Milestone 7 introduces the loop.

The teaching question is:

> When does LLM tool calling become an agent?

Not every LLM call is an agent. Not every tool call is an agent. MCP is not an agent framework.

The agent-like behavior starts when the host lets the model repeatedly decide, act, observe, and decide again.

## Before: One Tool Call

Milestone 6 used the model as a tool selector:

```text
LLM
  |
  v
one tool call
  |
  v
one observation
  |
  v
final answer
```

That proved the model could choose from MCP-discovered tools.

## Now: A Bounded Loop

Milestone 7 keeps calling the model until it either asks for another tool or produces a final answer:

```text
user question
  |
  v
LLM
  |
  v
tool call
  |
  v
MCP tool result / observation
  |
  v
LLM
  |
  v
another tool call OR final answer
```

The host owns this loop. The MCP servers do not change.

## Plain Python Loop

The implementation is intentionally small:

```python
for iteration in range(max_iterations):
    response = call_model(...)
    calls = extract_tool_calls(response)

    if not calls:
        return final_answer

    for call in calls:
        result = execute_mcp_tool(call)
        send_result_back_to_model(result)

return bounded_stop
```

This is not LangGraph. It is not Google ADK. It is not a planner/executor architecture.

It is a controlled software loop around model calls and MCP tool execution.

## What The Model Can Do Now

The model can combine information from multiple independent MCP servers.

For example, it can:

1. ask Trade MCP to find the HS code for lithium-ion batteries
2. ask Trade MCP for Germany imports from China for that HS code
3. ask World Bank MCP for Germany economic context
4. write a final answer using the observations

The model chooses the sequence. The host executes each requested tool. The servers remain independent.

The default demo keeps the question deliberately bounded: it asks for Germany's lithium-ion battery imports from China in 2023 and compares that value with Germany's 2023 GDP. That is enough to require multiple tools across both MCP servers without turning the demo into open-ended research.

## Safety Limits

The loop is bounded:

- `max_iterations = 5`
- `max_tool_calls_per_iteration = 2`

If the model keeps asking for tools, the host stops. If the model requests malformed arguments or an unknown tool, the host stops with a clear reason.

This is important. "Agent" should not mean "unbounded process."

When `max_iterations` is reached after a tool result, the host makes one final synthesis call with tools disabled. That final call cannot gather more data; it can only summarize what the loop has already observed. This keeps the safety limit intact while avoiding an abrupt ending.

## When Can We Reasonably Call This An Agent?

For this tutorial, it is reasonable to call Milestone 7 an agent loop because the model participates in repeated control flow:

- it reasons from the user question
- it chooses an action
- the host executes that action
- it observes the result
- it decides what to do next

That is the core agent pattern.

It is still a small agent loop, not a full production agent system.

## Buzzword Check

What changed:

- the host can run multiple model/tool iterations
- observations from one tool call can influence the next model decision
- the model can use both Trade and World Bank MCP servers in one answer
- the demo prints every decision and observation

What did not change:

- MCP still only exposes and invokes capabilities
- MCP does not decide which tool to call
- the MCP servers did not change
- the MCP servers do not call each other
- the domain clients did not change
- there is no LangGraph, Google ADK, memory, vector database, or multi-agent system

The magic-looking thing is ultimately just a loop.
