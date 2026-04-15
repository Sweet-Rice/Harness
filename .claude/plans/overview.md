# t.ai — Roadmap

## Current State

A working LLM harness with:
- **Inference abstraction** (L1 — DONE): Provider-agnostic `InferenceClient` with role-based model routing. OllamaProvider. TOML config.
- **MCP server** with auto-discovered tools (FastMCP)
- **Agent factory** (L6): Premade agents (planner, coder) spawned via `run_agent` virtual tool. Mmap-backed context switching — orchestrator saves context to mmap while agents run.
- **Supervisor**: Manages orchestrator ↔ agent context switching. Sequential execution, one loop at a time.
- **Plan file coordination**: PlanStore with ctrl/in_use/diff versioning. All agents read/write plans via MCP tools.
- **SQLite conversation persistence** (not yet migrated to abstract backend)
- **WebSocket + web UI** with markdown, streaming, thinking display
- **CLI interface** with conversation management

## Key Files (Post-Refactor)

| File | Purpose |
|------|---------|
| `harness/utils/llm.py` | Main loop, streaming, DelegationRequest, run_agent injection |
| `harness/utils/supervisor.py` | Context switch cycle: save → agent → restore |
| `harness/utils/agents.py` | AgentConfig, premade agent registry |
| `harness/utils/context_store.py` | Mmap-backed context store for agent switching |
| `harness/utils/inference.py` | InferenceProvider ABC, InferenceClient, StreamChunk, ToolCallInfo |
| `harness/utils/providers/ollama.py` | OllamaProvider implementation |
| `harness/config.py` | HarnessConfig, TOML loader, role-based model config |
| `harness/utils/prompts.py` | SYSTEM_PROMPT (orchestrator delegation instructions) |
| `harness/utils/context.py` | ConversationManager (SQLite, not yet abstracted) |
| `harness/utils/persistence.py` | PersistenceBackend ABC, SQLiteBackend, Document model |
| `harness/utils/plan_store.py` | PlanStore with ctrl/in_use/diff versioning |
| `harness/utils/logger.py` | Thinking log side channel |
| `harness/tools/files.py` | read_file, write_file |
| `harness/tools/search.py` | web_search (SearXNG), fetch_url |
| `harness/tools/plans.py` | Plan MCP tools (create, get, update, status, list, diffs) |
| `harness/server.py` | FastMCP server, tool auto-discovery |
| `harness/web/server.py` | WebSocket + HTTP server |
| `harness/web/static/index.html` | Frontend |
| `harness/harness.py` | CLI entry point |
| `harness.toml` | Provider + model + service config |

## Build Order

| Priority | Layer | Status | Next Step |
|----------|-------|--------|-----------|
| 1 | L1: Inference Abstraction | DONE | Add providers as needed |
| 2 | L5: Persistent Context Storage | PARTIAL | Migrate ConversationManager, build context file tree |
| 3 | L2: Tool Use | PARTIAL | Restore write approval, add shell tool |
| 4 | L3: Self-Correction | MINIMAL | Add reviewer agent, JSON validation |
| 5 | L6: Orchestration | PARTIAL | Test agent flow, add text_tool, iterate prompts |
| 6 | L4: Memory | NOT STARTED | Fact store, episodic memory, semantic graph |
| 7 | L7: Interface | PARTIAL | Fix write approval UI, agent status display, voice |

## Layer Dependencies

```
L1 (Inference) ✅ ─────────────────────┐
  │                                     │
  ▼                                     ▼
L2 (Tools)          L5 (Persistence) → L6 (Orchestration)
  │                   │
  ▼                   ▼
L3 (Self-Correction)  L4 (Memory)
                                        │
                                        ▼
                                  L7 (Interface)
```

- L1 DONE — unblocks everything
- L5 abstract interface done — PlanStore proves it works. ConversationManager migration is straightforward.
- L6 core infrastructure done — agents + supervisor + context switching. Needs real-world testing.
- L4 is the biggest remaining gap — fully designed but zero implementation.

## Immediate Priorities

1. **Test agent delegation end-to-end** — verify planner + coder flow works for real tasks
2. **Restore write approval flow** — `write_file` needs the proposal/diff/approve cycle back
3. **Iterate prompts** — agent and orchestrator prompts need tuning based on actual model behavior
4. **Migrate ConversationManager** — to PersistenceBackend, unblocking L4

## Open Questions
- **Vector store choice**: What backs the memory layer? Local (ChromaDB, FAISS) or external?
- **Tool permissions**: Per-agent tool filtering is done. Need dangerous-action confirmation for shell, email, etc.
- **Agent prompt tuning**: How well do qwen3.5/qwen3-coder follow the agent prompts? Need empirical testing.
