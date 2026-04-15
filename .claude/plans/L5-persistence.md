# Layer 5: Persistent Context Storage

## Purpose
An abstraction layer for storing and retrieving context that persists across sessions, conversations, and agent invocations. The abstraction matters because the underlying storage will change — flat files, SQLite, vector store, something purpose-built. Nothing above this layer should know or care what's underneath.

## Status
PARTIAL

## What Exists

### Abstract Persistence Interface (`harness/utils/persistence.py`)
- **Document model**: `Document(id, collection, data, metadata, created_at, updated_at)` — universal unit of persistence
- **PersistenceBackend ABC**: `write()`, `read()`, `query()`, `delete()` — abstract interface
- **SQLiteBackend**: Single `documents` table with JSON columns, `json_extract()` for metadata filtering, composite PK `(collection, id)`
- **`new_id()`**: Short UUID helper matching project convention

### Plan File Versioning (`harness/utils/plan_store.py`)
- **PlanStore** class using PersistenceBackend with two collections: `plans`, `plan_diffs`
- **ctrl/in_use/diff model**: `create()` saves immutable ctrl snapshot + mutable in_use copy; `update()` appends full before/after diff
- **Methods**: `create()`, `get()`, `update()`, `set_status()`, `get_diffs()`, `get_ctrl()`, `list_plans()`, `delete()`

### Plan MCP Tools (`harness/tools/plans.py`)
- Tools: `create_plan`, `get_plan`, `update_plan`, `set_plan_status`, `list_plans`, `get_plan_diffs`
- Auto-discovered by MCP server
- Used by both planner and coder agents as shared coordination state

### Mmap Context Store (`harness/utils/context_store.py`)
- **ContextStore** class — mmap-backed single-slot store for agent context switching
- `save(key, messages)` — serializes messages to mmap, frees Python heap
- `load(key)` — deserializes messages from mmap
- Auto-grows if payload exceeds initial allocation (4MB default)
- Used by supervisor for orchestrator context switching during agent delegation

### ConversationManager (`harness/utils/context.py`)
- SQLite backend at `harness/conversations.db` (not yet migrated to PersistenceBackend)
- Two tables: `conversations` (id, name, created_at, updated_at) and `messages` (id, conversation_id, role, content, position)
- Methods: `new()`, `load()`, `save()`, `list()`, `delete()`, `rename()`
- Used by both CLI (`harness/harness.py`) and web server (`harness/web/server.py`)

### Other
- **Thinking log** in `harness/utils/logger.py` — appends to `thinking.log` file (flat file, no abstraction)

## What's Planned

### Context File Tree
A persistent structure that stores context on files — what the system knows about the project it's operating on. Injected into and modified by agents.
  - Location: `harness/utils/file_context.py` (new)
  - Depends on: abstract persistence interface

### Decouple Conversation Storage
Refactor `ConversationManager` to use the abstract persistence interface instead of raw SQLite.
  - Location: refactor `harness/utils/context.py`
  - Depends on: abstract interface (done)

### Additional Backends
- Flat file backend
- Vector store backend (for memory embeddings — L4)
  - Location: `harness/utils/backends/` (new)
  - Depends on: abstract interface (done)

## Architecture
```
Memory (L4)     Orchestration (L6)     Conversations     File Context
  │                   │                     │                 │
  ▼                   ▼                     ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              Persistent Context Storage (abstract)              │
│         read()  write()  query()  delete()                      │
└─────────────────────────────────────────────────────────────────┘
  │                   │                     │
  ▼                   ▼                     ▼
SQLite Backend    File Backend       Vector Store Backend

Mmap Context Store (separate — raw memory for context switching)
  └─ Used by supervisor for agent delegation
```

## Key Decisions
- **SQLite as initial backend**: Already working. Proven, zero-config, single-file.
- **Abstraction before expansion**: Interface built and proven with PlanStore. Ready for new backends.
- **Mmap for context switching**: Separate from PersistenceBackend — purpose-built for agent delegation, not general persistence.
- **Plan versioning is database-backed**: ctrl/in_use/diff stored as documents in SQLiteBackend, not as files on disk.

## Open Questions
- How does the context file tree get populated — static analysis, agent observation, or both?
- What's the query interface for the vector store backend — raw similarity search or structured queries?
