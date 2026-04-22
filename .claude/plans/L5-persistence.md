# Layer 5: Persistent Context Storage

## Purpose

An abstraction layer for storing and retrieving context across sessions, conversations, and orchestrated runs. The backend will change; nothing above this layer should need to care.

## Status

PARTIAL

## What Exists

### Typed Conversation Persistence

- `harness/utils/persistence/base.py`
  Conversation repository protocol plus plan-store protocol
- `harness/utils/persistence/sqlite_conversations.py`
  SQLite-backed typed thread/message persistence
- `harness/utils/context/`
  `ConversationManager`, typed thread/message models, and compatibility loading/saving

The current thread model already distinguishes:
- `global_thread`
- `client_scratch`

and persists:
- message role/content
- message type
- tool-call payloads
- tool/tool-name metadata
- source/client identity

### Plan Store

- `harness/utils/persistence/plan_store.py`
  File-backed `ctrl` / `in_use` / diff-log workspace storage for orchestrated work

## What's Planned

### Broader Storage Boundary

- Keep expanding persistence behind stable interfaces rather than ad hoc SQL or raw file access in callers
- Add additional backends later if needed

### Plan File Versioning

The core orchestration model still uses:
- **ctrl** — immutable baseline snapshot
- **in_use** — live copy
- **appended diff** — audit log of changes over time

The first file-backed implementation now exists; future work should deepen it instead of replacing it with chat-history inference.

### Context File Tree

A persistent structure that stores what the system knows about project files and technical context.

### Persistence For Memory

Memory tiers in L4 should reuse this persistence boundary rather than inventing their own storage path.

## Architecture

```
Conversations / Threads     Plan Store     File Context     Memory
        │                      │               │              │
        ▼                      ▼               ▼              ▼
┌───────────────────────────────────────────────────────────────┐
│                 Persistent Context Storage                    │
└───────────────────────────────────────────────────────────────┘
        │                      │               │
        ▼                      ▼               ▼
  SQLite backend         File-backed plans   Future backends
```

## Key Decisions

- Typed thread/message persistence stays separate from plan-state persistence
- Plan workspaces are file-backed because that best matches the ctrl/in_use/diff design
- `ConversationManager` remains a compatibility surface, not the canonical owner of orchestrated plan state

## Open Questions

- Should plan workspaces gain SQLite indexing or stay purely file-driven?
- How should file context be populated: static analysis, agent observation, or both?
- What query surface will memory backends need from persistence?
