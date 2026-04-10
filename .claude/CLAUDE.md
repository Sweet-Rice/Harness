# t.ai

A harness that turns a local LLM into a personal AI assistant — "T.ai" The harness is the product; the model is swappable. A good harness makes a small model outperform a large model running naked.

## Core Idea

A bare LLM is just text-in, text-out. It can't remember, can't act, can't plan, can't check its own work. The harness provides all of that externally. Every cognitive weakness of the LLM becomes a tool or a harness rule, not a hope that the prompt will be followed.

## Principles

- The harness is model-agnostic. Never couple to one provider.
- Tools are the unit of capability. Adding a tool should be trivial.
- Tools are also the unit of abstraction. If the LLM is bad at something cognitively, externalize it into a tool.
- State lives in the plan file, not in chat history. Chat history is how you got somewhere; the plan file is where you are.
- Persistent context storage is an abstraction. The backend will change; nothing above it should break.
- The orchestrator delegates; it doesn't do work directly.
- Write operations require explicit user approval — no silent file modifications.
- All file paths must be absolute.
- Every action is logged.
- The user's own plans and architecture decisions take precedence.

## Stack

- **Language:** Python
- **LLM:** Local models via Ollama — Gemma 4 (orchestrator), Qwen 3 Coder (code tasks)
- **Delivery:** MCP server (FastMCP)
- **Storage:** SQLite (conversations), vector store (memory — planned)
- **Web:** WebSocket server + static HTML frontend
- **Deps:** `ollama`, `fastmcp`, `websockets`

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

## Key Files

| File | Purpose |
|------|---------|
| `harness/utils/llm.py` | Main tool-calling loop, streaming, proposal handling |
| `harness/utils/prompts.py` | SYSTEM_PROMPT (orchestrator instructions) |
| `harness/utils/context.py` | ConversationManager (SQLite persistence) |
| `harness/utils/logger.py` | Thinking log side channel |
| `harness/tools/plan.py` | plan() + plan_review() with their prompts |
| `harness/tools/output.py` | output() (inner tool loop) + output_review() |
| `harness/tools/files.py` | read_file + write_file (proposal-based) |
| `harness/tools/review.py` | review_code tool |
| `harness/tools/thinking.py` | Extended thinking toggle |
| `harness/server.py` | FastMCP server, tool auto-discovery |
| `harness/web/server.py` | WebSocket + HTTP server, approval queue wiring |
| `harness/web/static/index.html` | Frontend (streaming, markdown, diff display, conversations) |
| `harness/harness.py` | CLI entry point (with terminal approval prompt) |

## Running

```bash
# Start MCP server
uv run python -m harness.server

# Start web UI
uv run python -m harness.web.server
```
