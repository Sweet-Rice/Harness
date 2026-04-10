# Layer 6: Planning & Orchestration

## Purpose
The orchestrator (Gemma 4) receives tasks, writes plans, delegates to sub-agents, and manages execution. State lives in the plan file, not in chat history. The orchestrator delegates; it doesn't do work directly.

## Status
PARTIAL

## What Exists

### Main Loop (`harness/utils/llm.py`)
- `loop()`: Async tool-calling orchestrator (MAX_TOOL_ROUNDS = 15)
- `_stream()`: Calls `ollama.chat(stream=True)`, emits events via `on_event` callback
- `get_tools()`: Fetches tool list from MCP client
- `set_thinking()`: Global toggle for extended thinking mode
- No hardcoded phase logic — the model decides when to call plan, output, review

### System Prompt (`harness/utils/prompts.py`)
- Single `SYSTEM_PROMPT` dict instructing the orchestrator to: plan → review → output → review
- ~12 lines, minimal

### Orchestration Tools
- `plan(intent)` in `harness/tools/plan.py` — generates numbered step-by-step plan via `ollama.chat()`
- `plan_review(plan, intent)` in `harness/tools/plan.py` — validates plan, returns VERDICT: PASS/FAIL
- `output(plan, intent)` in `harness/tools/output.py` — executes plan with inner tool loop (MAX_INNER_ROUNDS = 10), has access to read_file/write_file
- `output_review(output, plan, intent)` in `harness/tools/output.py` — validates output

### Streaming Events
| Event | Purpose |
|-------|---------|
| `stream_start` | Frontend creates message div |
| `stream_token` | Incremental text token |
| `stream_thinking` | Thinking token (extended thinking mode) |
| `stream_end` | Frontend does final markdown render |
| `log` | Debug info, tool results, review verdicts |
| `message` | Final response (for conversation history/replay) |
| `status` | Phase indicator: `cooking`, `idle` |
| `proposal` | Write proposal — frontend renders diff + approve/deny |

### Write Approval Flow
```
write_file(path, content) → proposal JSON (diff + command)
  │
  ├─ Main loop sends "proposal" event to frontend
  ├─ Frontend renders git-style diff + Approve/Deny buttons
  ├─ User clicks → WebSocket sends response → approval_queue
  │
  └─ Approved: pathlib writes file
     Denied: LLM told "User denied write"
```

### Current Control Flow
```
User message
  │
  ▼
Orchestrator LLM (with all tools available)
  │
  ├─ calls plan(intent)
  │   └─ internal ollama.chat() → returns numbered plan
  │
  ├─ calls plan_review(plan, intent)
  │   └─ internal ollama.chat() → returns VERDICT: PASS/FAIL
  │   └─ if FAIL: orchestrator calls plan() again
  │
  ├─ calls output(plan, intent)
  │   └─ internal ollama.chat() with tools (read_file, write_file)
  │   └─ runs its own inner tool loop (max 10 rounds)
  │   └─ write proposals collected, returned to main loop for user approval
  │
  ├─ calls output_review(output, plan, intent)
  │   └─ internal ollama.chat() → returns VERDICT: PASS/FAIL
  │   └─ if FAIL: orchestrator calls output() again
  │
  └─ presents final output as text response
```

## What's Planned

### Plan File Versioning
Three-copy system for agent state management:
- **ctrl** — immutable snapshot before changes (the baseline)
- **in_use** — live copy modified by agents during execution
- **appended diff** — log of diffs (ctrl vs in_use) for auditability and rollback
  - Location: `harness/utils/plan_store.py` (new)
  - Depends on: L5 (persistent context storage)

### Sub-Agent Delegation
The orchestrator creates sub-agents with:
- Their own system prompts (task-specific)
- Their own tool permissions (restricted per task)
- Potentially different models (Qwen 3 Coder for code, Gemma for reasoning)
- Results flow back to the orchestrator, which updates the plan file
  - Location: `harness/utils/agents.py` (new)
  - Depends on: L1 (per-task model routing), L5 (plan file storage)

### Target Control Flow
```
User message
  │
  ▼
Orchestrator (Gemma 4)
  │
  ├─ Writes plan file (ctrl snapshot created)
  │
  ├─ Feeds plan to sub-agent (prompted for step 1)
  │   └─ Sub-agent works, returns tool calls
  │   └─ Orchestrator updates in_use plan file
  │   └─ Diff appended to log
  │
  ├─ Repeats for each step (or delegates multiple in parallel)
  │
  ├─ text_tool runs summarization pass
  │   └─ Reads accumulated diffs
  │   └─ Produces concise summary
  │   └─ Appends to persistent context
  │   └─ Infers next steps
  │
  └─ Orchestrator produces final response
```

### text_tool (Summarization)
A dedicated summarization pass, separate from the orchestrator:
- Reads accumulated diffs from the plan file
- Produces a concise summary of what happened
- Appends that summary to persistent context
- Uses the summary to infer next steps and suggest actions
- Keeps summarization out of the orchestrator's loop so it doesn't burn planning capacity on compression
  - Location: `harness/tools/text_tool.py` (new)
  - Depends on: L5 (persistent context), plan file versioning

### Context File Tree
A persistent structure storing context on project files. Injected into and modified by agents as working memory for the project.
  - Location: `harness/utils/file_context.py` (new)
  - Depends on: L5

## Key Decisions
- **Orchestrator doesn't do work directly**: It delegates to tools and sub-agents
- **State in plan files, not chat history**: Chat history is how you got somewhere; the plan file is where you are
- **Tools wrap their own LLM calls**: Each orchestration tool (plan, output, review) calls `ollama.chat()` directly
- **No hardcoded phase logic**: The main loop is a generic tool-calling loop; the model decides sequencing

## Open Questions
- How do sub-agents report progress back to the orchestrator? Streaming events, return values, or plan file updates?
- Should sub-agents be able to spawn their own sub-agents? If so, what's the max delegation depth?
- How does the orchestrator decide when a plan step is "done" vs needs retry?
- text_tool: should it run after every step, or only at the end?
