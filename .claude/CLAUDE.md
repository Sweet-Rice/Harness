# t.ai

A harness that turns a local LLM into a personal AI assistant. The harness is the product; the model is swappable. A good harness makes a small model outperform a large model running naked.

## Core Idea

A bare LLM is just text-in, text-out. It cannot remember, act, plan, or check its own work reliably. The harness provides those capabilities externally. Every cognitive weakness of the LLM becomes a tool, a policy, or a persistence rule rather than a prompt hope.

## Principles

- The harness is model-agnostic. Never couple to one provider.
- Tools are the unit of capability. Adding a tool should be trivial.
- Tools are also the unit of abstraction. If the LLM is bad at something cognitively, externalize it into a tool.
- State lives in the plan file, not in chat history. Chat history is how you got somewhere; the plan file is where you are.
- Persistent context storage is an abstraction. The backend will change; nothing above it should break.
- The orchestrator delegates; it does not do work directly.
- Write operations require explicit user approval — no silent file modifications.
- All file paths must be absolute.
- Every action is logged.
- The user's own plans and architecture decisions take precedence.

## Stack

- **Language:** Python
- **LLM:** Local models via Ollama today, behind an inference abstraction
- **Delivery:** MCP server (FastMCP)
- **Storage:** SQLite for typed thread/message persistence, file-backed plan storage for orchestrated work, vector store planned for memory
- **Interfaces:** WebSocket + static web frontend, Discord client
- **Deps:** `ollama`, `fastmcp`, `websockets`, `discord.py`

## Architecture Snapshot

The repo has already gone through a modularization pass. The roadmap is unchanged, but the implementation now lives behind these seams:

- `harness/utils/inference/`
  Provider abstraction and model-role registry
- `harness/utils/loop/`
  Generic MCP-first conversation engine
- `harness/utils/orchestration/`
  Harness policy, prompts, delegation, skills, and orchestrated plan-state services
- `harness/utils/persistence/`
  Durable storage boundaries for thread/message persistence and plan workspaces
- `harness/utils/context/`
  Typed thread/message records plus the `ConversationManager` compatibility surface
- `harness/utils/llm.py`
  Thin compatibility entrypoint into the shared loop

Plan docs below are aligned to this modular snapshot.

## Architecture Layers

| # | Layer | Plan File | Status |
|---|-------|-----------|--------|
| 1 | Inference Abstraction | [L1-inference.md](plans/L1-inference.md) | PARTIAL |
| 2 | Tool Use | [L2-tools.md](plans/L2-tools.md) | PARTIAL |
| 3 | Self-Correction | [L3-self-correction.md](plans/L3-self-correction.md) | PARTIAL |
| 4 | Memory | [L4-memory.md](plans/L4-memory.md) | NOT STARTED |
| 5 | Persistent Context Storage | [L5-persistence.md](plans/L5-persistence.md) | PARTIAL |
| 6 | Planning & Orchestration | [L6-orchestration.md](plans/L6-orchestration.md) | PARTIAL |
| 7 | User Interface | [L7-interface.md](plans/L7-interface.md) | PARTIAL |

Roadmap and build order: [overview.md](plans/overview.md)

## Key Files and Surfaces

| Surface | Purpose |
|---------|---------|
| `harness/utils/llm.py` | Thin shared loop entrypoint used by clients |
| `harness/utils/inference/` | Provider abstraction and model-role lookup |
| `harness/utils/loop/` | Streaming, tool registration, dispatch, and conversation-state mutation |
| `harness/utils/orchestration/policy.py` | Client- and mode-aware orchestration policy |
| `harness/utils/orchestration/delegation.py` | Restricted sub-agent pseudo-tool |
| `harness/utils/orchestration/skills.py` | Shared skill trigger layer |
| `harness/utils/orchestration/plan_state.py` | Plan-first orchestration service and run/session bridge |
| `harness/utils/context/` | Typed thread/message models and `ConversationManager` |
| `harness/utils/persistence/sqlite_conversations.py` | SQLite-backed thread/message repository |
| `harness/utils/persistence/plan_store.py` | File-backed `ctrl` / `in_use` / diff plan workspace storage |
| `harness/tools/files.py` | Absolute-path file tools with structured non-mutating write proposals |
| `harness/server.py` | FastMCP server, tool auto-discovery |
| `harness/web/server.py` | WebSocket + HTTP server, orchestrated global-thread path |
| `harness/discord/bot.py` | Discord client, slash commands, default-deny tool policy |

## Running

```bash
# Start MCP server
uv run python -m harness.server

# Start web UI
uv run python -m harness.web.server

# Start Discord bot
uv run python -m harness.discord
```
