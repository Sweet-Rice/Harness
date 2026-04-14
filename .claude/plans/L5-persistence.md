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

### ConversationManager (`harness/utils/context.py`)
- SQLite backend at `harness/conversations.db` (not yet migrated to PersistenceBackend)
- Two tables: `conversations` (id, name, created_at, updated_at) and `messages` (id, conversation_id, role, content, position)
- Methods: `new()`, `load()`, `save()`, `list()`, `delete()`, `rename()`
- Used by both CLI (`harness/harness.py`) and web server (`harness/web/server.py`)

### Other
- **Thinking log** in `harness/utils/logger.py` — appends to `thinking.log` file (flat file, no abstraction)

## What's Planned

### Abstract Persistence Interface
- **Read/write/query/delete** — the four operations. Everything that needs persistence goes through this interface.
  - Location: `harness/utils/persistence.py` (new)
  - Depends on: nothing
- **Multiple storage backends**: Start with SQLite (already exists), add flat file and vector store backends as needed.
  - Location: backend implementations under `harness/utils/backends/` (new)
  - Depends on: abstract interface

### Plan File Versioning
The t.ai orchestration model uses plan files with three copies:
- **ctrl**: The plan file before any changes. Immutable snapshot. The baseline.
- **in_use**: The live copy that changes dynamically as agents iterate.
- **appended diff**: A log of diffs from each iteration (ctrl vs in_use). Full auditability and rollback.
  - Location: `harness/utils/plan_store.py` (new)
  - Depends on: abstract persistence interface

### Context File Tree
A persistent structure that stores context on files — what the system knows about the project it's operating on. Injected into and modified by agents.
  - Location: `harness/utils/file_context.py` (new)
  - Depends on: abstract persistence interface

### Decouple Conversation Storage
Refactor `ConversationManager` to use the abstract persistence interface instead of raw SQLite.
  - Location: refactor `harness/utils/context.py`
  - Depends on: abstract interface

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
(conversations)   (plan files)       (memory embeddings)
```

## Key Decisions
- **SQLite as initial backend**: Already working for conversations. Proven, zero-config, single-file.
- **Abstraction before expansion**: Build the interface before adding new storage types. Refactor ConversationManager to prove the abstraction works.

## Open Questions
- Should plan file versioning be file-based (three actual files on disk) or database-backed (versions as rows)?
- How does the context file tree get populated — static analysis, agent observation, or both?
- What's the query interface for the vector store backend — raw similarity search or structured queries?
