# `context`

This package owns in-memory conversation state and the compatibility conversation-management surface used by callers.

## Files

- `__init__.py`
  Exposes `ConversationManager` as the compatibility layer for web and Discord callers. It coordinates with `persistence/` and injects the default orchestrator system prompt on load.
- `conversation_state.py`
  Re-exports the shared `ConversationState` object used by the loop engine. This keeps callers importing state from a context-focused namespace.

## Relationship to adjacent directories

- Works with `persistence/` for durable storage.
- Supplies state objects to `loop/`.
- Uses prompt defaults from `orchestration/`.

This package should not contain SQL or provider-specific inference logic.
