# t.ai — Roadmap

## Current State

A working LLM coding harness (~728 lines of Python) with:
- MCP server with auto-discovered tools (FastMCP)
- Orchestrator loop: plan → plan_review → output → output_review
- SQLite conversation persistence
- WebSocket + web UI with markdown rendering, streaming, thinking display
- CLI interface with conversation management
- File I/O tools (read/write with proposal-based approval)
- Code review, thinking toggle, ping tools

The model is hardcoded to `qwen3-coder` via `ollama.AsyncClient`. There is no memory, no persistence abstraction, no sub-agent delegation, no voice interface.

## Build Order

Following the stated principle: inference → tools → self-correction → persistent context → memory → orchestration → voice.

| Priority | Layer | Rationale |
|----------|-------|-----------|
| 1 | L1: Inference Abstraction | Everything depends on this — model-agnostic interface before adding features |
| 2 | L5: Persistent Context Storage | Memory (L4) and orchestration (L6) both need a storage abstraction |
| 3 | L2: Tool Use | Expand tool inventory (shell, web search, etc.) |
| 4 | L3: Self-Correction | Harden validation and error recovery |
| 5 | L4: Memory | Vector store, episodic memory, user model — requires L5 |
| 6 | L6: Orchestration | Plan file versioning, sub-agents, text_tool — requires L1, L4, L5 |
| 7 | L7: Interface | Voice (STT/TTS), mobile — polish layer, build last |

## Layer Dependencies

```
L1 (Inference) ──────────────────────────┐
  │                                       │
  ▼                                       ▼
L2 (Tools)          L5 (Persistence) → L6 (Orchestration)
  │                   │
  ▼                   ▼
L3 (Self-Correction)  L4 (Memory)
                                          │
                                          ▼
                                    L7 (Interface)
```

- L1 is foundational — model abstraction before anything else
- L5 before L4 — memory needs a persistence backend
- L5 before L6 — plan file versioning needs persistent storage
- L1 before L6 — sub-agent model routing needs inference abstraction
- L7 is independent but benefits from all other layers being stable

## Open Questions

- **Model selection**: Gemma 4 as orchestrator, Qwen 3 Coder for code tasks — is this fixed or should the system auto-select based on task type?
- **Vector store choice**: What backs the memory layer? Local (ChromaDB, FAISS) or external?
- **Plan file format**: The ctrl/in_use/diff versioning scheme — is this file-based or database-backed?
- **Tool permissions**: Per-agent tool permission model — allowlist or denylist?
- **Dangerous action confirmation**: Which tools require user approval beyond write_file? (shell, email, home automation)
