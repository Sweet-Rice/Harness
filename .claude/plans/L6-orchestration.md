# Layer 6: Planning & Orchestration

## Purpose
The orchestrator receives tasks, triages complexity, delegates to specialized agents, and reviews results. State lives in the plan file, not in chat history. The orchestrator delegates; it doesn't do work directly.

## Status
PARTIAL — core infrastructure done, needs testing and iteration

## What Exists

### Main Loop (`harness/utils/llm.py`)
- `loop()`: Async tool-calling loop with streaming events
- `_stream()`: Calls `InferenceClient.stream()` (provider-agnostic), emits events
- `get_tools()`: Fetches tool list from MCP client
- `_build_run_agent_tool()`: Dynamically builds `run_agent` virtual tool from agent registry
- `DelegationRequest`: Returned when orchestrator calls `run_agent` — signals context switch
- `allowed_tools` parameter: When `None` (orchestrator), injects `run_agent`. When a list (agent), filters MCP tools to that set — prevents recursion.
- Returns `None` on normal finish, `DelegationRequest` on delegation

### Supervisor (`harness/utils/supervisor.py`)
- `run()`: Runs orchestrator loop with context-switching agent delegation
- Context switch cycle:
  1. Orchestrator calls `run_agent` → loop returns `DelegationRequest`
  2. Supervisor saves orchestrator messages to mmap (frees Python heap)
  3. Agent runs in its own `loop()` with own system prompt, role, and filtered tools
  4. Agent finishes → supervisor restores orchestrator from mmap
  5. Agent output appended as tool response → orchestrator resumes
- Only one loop active at a time (sequential, limited hardware)

### Agent Factory (`harness/utils/agents.py`)
- `AgentConfig` dataclass: name, description, system_prompt, role, allowed_tools, max_rounds
- Premade agents:
  - **planner** (role=orchestrator): Generates and validates plans. Tools: create_plan, update_plan, get_plan, read_file, web_search, fetch_url
  - **coder** (role=coder): Executes coding tasks. Tools: read_file, write_file, get_plan, update_plan, web_search, fetch_url
- `get_agent(name)`, `list_agents()`

### Mmap Context Store (`harness/utils/context_store.py`)
- `ContextStore`: Mmap-backed single-slot store for context switching
- `save(key, messages)` / `load(key)` — serialize/deserialize message lists
- Auto-grows allocation if payload exceeds 4MB default
- Data stays in OS page cache — no GC pressure

### System Prompt (`harness/utils/prompts.py`)
- Orchestrator prompt: triage simple vs complex, delegate via `run_agent("planner")` then `run_agent("coder")`, review via plan file

### Streaming Events
| Event | Purpose |
|-------|---------|
| `stream_start` | Frontend creates message div |
| `stream_token` | Incremental text token |
| `stream_thinking` | Thinking token (extended thinking mode) |
| `stream_end` | Frontend does final markdown render |
| `log` | Debug info, tool results, delegation events |
| `message` | Final response (for conversation history/replay) |
| `status` | Phase indicator: `cooking`, `agent:<name>`, `idle` |

### Control Flow
```
User message
  │
  ▼
supervisor.run(client, messages, on_event)
  │
  ├─ loop(client, messages, on_event)           ← orchestrator
  │    ├─ Simple task → answers directly → return None
  │    └─ Complex task → run_agent("planner", task) → return DelegationRequest
  │
  ├─ store.save("orchestrator", messages)        ← mmap context switch
  ├─ messages.clear()                            ← free Python heap
  │
  ├─ loop(client, agent_messages, on_event,      ← planner agent
  │       role="orchestrator", allowed_tools=[...])
  │    └─ creates plan, validates it, returns
  │
  ├─ store.load("orchestrator")                  ← restore from mmap
  ├─ messages.append(agent output)
  │
  ├─ loop(client, messages, on_event)            ← orchestrator resumes
  │    └─ reviews plan, runs run_agent("coder", ...)
  │
  ├─ [context switch again for coder agent]
  │
  └─ orchestrator presents final result → return None
```

## What's Planned

### text_tool (Summarization)
A dedicated summarization pass, separate from the orchestrator:
- Reads accumulated diffs from the plan file
- Produces a concise summary of what happened
- Appends that summary to persistent context
- Keeps summarization out of the orchestrator's loop
  - Location: `harness/tools/text_tool.py` (new)
  - Depends on: L5 (persistent context)

### Context File Tree
A persistent structure storing context on project files. Injected into and modified by agents as working memory.
  - Location: `harness/utils/file_context.py` (new)
  - Depends on: L5

### Additional Agents
- **reviewer** agent: Dedicated verification using reviewer role (different model). For L3 self-correction.
- **shell** agent: For executing shell commands with safety checks.
- Custom agent creation: Agent factory could support dynamic creation, not just premade agents.

## Key Decisions
- **Orchestrator doesn't do work directly**: Delegates to agents via `run_agent`
- **State in plan files, not chat history**: Agents coordinate via PlanStore. Orchestrator reviews via `get_plan()`.
- **Context switching via mmap**: Orchestrator context saved to mmap during agent execution. One inference at a time.
- **No nested agents**: Agents cannot call `run_agent`. Only the orchestrator delegates.
- **Sequential execution**: Limited hardware — no concurrent agents. Concurrency only for independent I/O (web search).
- **Self-contained agents**: Each agent handles its full sub-workflow. Orchestrator reviews output.
- **Virtual tool pattern**: `run_agent` is injected into the tool list but intercepted before MCP dispatch. Clean separation.

## Open Questions
- How does the orchestrator handle multi-step plans where some steps fail?
- Should agents have access to conversation history or only their task description?
- text_tool: run after every agent, or only at the end?
- Max delegation depth if we ever allow agents to delegate?
