# `persistence`

This package owns durable storage concerns. The rest of the harness should treat it as the storage boundary rather than reaching directly into SQLite.

## Files

- `__init__.py`
  Public import surface for the current SQLite repository.
- `base.py`
  Repository protocols describing thread/message persistence and plan-store contracts.
- `sqlite_conversations.py`
  SQLite-backed implementation for typed threads and typed message records, including thread type/mode, source identity, and tool-call payloads.
- `plan_store.py`
  File-backed plan workspace storage for canonical orchestrated task state (`ctrl`, `in_use`, diff history, metadata).

## Relationship to adjacent directories

- `context/` uses this package to save and load conversations.
- `orchestration/` uses the plan store for plan-first orchestrated runs.
- `loop/` should not import this package directly.
- `orchestration/` should treat persistence as an implementation detail unless a future feature explicitly needs storage coordination.

If you add another backend later, it should be another repository implementation here rather than new SQL in caller code.
