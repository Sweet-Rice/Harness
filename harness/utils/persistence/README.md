# `persistence`

This package owns durable storage concerns. The rest of the harness should treat it as the storage boundary rather than reaching directly into SQLite.

## Files

- `__init__.py`
  Public import surface for the current SQLite repository.
- `base.py`
  Repository protocol describing the conversation-storage contract.
- `sqlite_conversations.py`
  SQLite-backed implementation for typed threads and typed message records, including thread type/mode, source identity, and tool-call payloads.

## Relationship to adjacent directories

- `context/` uses this package to save and load conversations.
- `loop/` should not import this package directly.
- `orchestration/` should treat persistence as an implementation detail unless a future feature explicitly needs storage coordination.

If you add another backend later, it should be another repository implementation here rather than new SQL in caller code.
