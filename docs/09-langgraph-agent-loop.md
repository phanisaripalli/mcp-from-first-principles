# 09 - Rebuilding The Agent Loop With LangGraph

Milestone 8 rebuilds the Milestone 7 agent loop with LangGraph.

The teaching question is:

> We already built a working agent loop in plain Python. What does LangGraph actually add?

The short answer: LangGraph changes how the control loop is structured. It does not make the model smarter, and it does not change MCP.

## Plain Python Loop

Milestone 7 represented the loop directly:

```text
while not finished:
    call LLM
    if tool requested:
        execute MCP tool
        add observation
    else:
        return answer
```

The state lived in local variables:

- previous response id
- next model input
- tool calls
- tool observations
- accumulated trace steps
- final answer
- stop reason

That version is easy to read because the workflow is still small.

## LangGraph Loop

Milestone 8 represents the same control flow as a graph:

```text
START
  |
  v
model
  |
  | tool calls requested
  v
tools
  |
  | continue
  v
model

model
  |
  | final answer
  v
END

tools
  |
  | max iterations reached
  v
synthesize
  |
  v
END
```

The loop is still the same idea:

```text
reason -> act -> observe -> reason again
```

The difference is that LangGraph gives names to the pieces of the loop:

- state
- nodes
- edges
- conditional routing
- graph compilation
- graph invocation

## State

The LangGraph implementation uses explicit graph state. Instead of local variables inside one loop, each node receives a state object and returns updates to that state.

That makes the workflow boundary clearer:

- `model` reads the current input and may produce tool calls
- `tools` executes MCP tools and writes observations
- `synthesize` writes a final answer when the graph has reached its tool-use limit

## Nodes

The graph has three nodes:

- `model`: calls the OpenAI Responses API with MCP-discovered tools
- `tools`: executes model-requested tools through the existing MCP router
- `synthesize`: asks for a final no-tools answer when the iteration limit is reached

The MCP servers are not LangGraph nodes. They remain ordinary MCP servers behind the routing layer.

## Edges

The graph uses conditional edges:

- after `model`, go to `tools` if the model requested tools
- after `model`, end if the model produced a final answer
- after `tools`, go back to `model` if more iterations are allowed
- after `tools`, go to `synthesize` if the tool-use limit has been reached

This is the same loop as Milestone 7, but the cycle is visible in the graph.

## What LangGraph Adds

LangGraph adds structure around orchestration:

- an explicit state object
- named nodes
- named routing decisions
- a compiled graph
- framework-managed movement from node to node
- a natural place to add branching later

For a tiny loop, this is more code than plain Python. For a larger workflow, it can make the shape easier to reason about.

## What LangGraph Does Not Add

LangGraph does not change the underlying capabilities:

- the LLM is still the LLM
- MCP servers are unchanged
- World Bank API logic is unchanged
- Trade API logic is unchanged
- tool schemas are unchanged
- tools do not become more accurate
- MCP is still not an agent framework
- LangGraph is not required for MCP
- LangGraph is not required to build an agent

The model still chooses tools probabilistically from names, descriptions, and schemas. The host still executes those choices.

## Side-By-Side

| Question | Plain Python Agent | LangGraph Agent |
| --- | --- | --- |
| Where does state live? | Local variables in `answer()` | Explicit graph state |
| How does looping work? | `for` loop | `tools -> model` edge |
| How does termination work? | `if` statements and returns | conditional edges to `END` |
| How easy is it to read now? | Very easy for a small loop | Slightly heavier |
| How easy is it to extend later? | Can become tangled | Nodes and edges help separate paths |
| Where is MCP logic? | Existing MCP router | Existing MCP router |
| Is the model smarter? | No | No |
| Is this required for MCP? | No | No |

## Could We Have Done This Without LangGraph?

Yes. Milestone 7 proves it.

The plain Python loop is a real agent loop. It lets the model decide, act through tools, observe results, and decide again.

## So Why Use LangGraph?

LangGraph starts to become useful when the control flow grows:

- branching workflows
- checkpoints
- persistence
- resumable runs
- human review steps
- richer shared state
- different paths for different failure types

This milestone does not implement those features. It only shows where they would fit.

## Buzzword Check

```text
Plain Python agent:
    explicit control loop

LangGraph agent:
    same fundamental loop represented as a state graph
```

No magic was added to the model. No magic was added to MCP. The abstraction changed the shape of the orchestration code.
