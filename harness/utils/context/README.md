# `context`

This package owns in-memory conversation state and the compatibility conversation-management surface used by callers.

## Files

- `__init__.py`
  Exposes `ConversationManager` as the compatibility layer for web and Discord callers. It coordinates with `persistence/` and manages explicit thread types, modes, and client/source identity.
- `conversation_state.py`
  Re-exports the shared `ConversationState` object used by the loop engine. This keeps callers importing state from a context-focused namespace.
- `models.py`
  Defines the typed `ThreadRecord`, `MessageRecord`, and `ConversationThread` structures used across context, persistence, and loop boundaries.

## Relationship to adjacent directories

- Works with `persistence/` for durable storage.
- Supplies state objects to `loop/`.
- Carries thread mode information that `orchestration/` uses to choose the correct prompt and policy.

This package should not contain SQL or provider-specific inference logic.
