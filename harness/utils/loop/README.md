# `loop`

This package is the generic conversation engine. It should remain policy-agnostic and focused on the mechanics of running a tool-capable LLM loop.

## Files

- `__init__.py`
  Public import surface for the shared runner.
- `runner.py`
  Core loop execution. Streams model output, records assistant/tool messages, dispatches tool calls, and emits events.
- `state.py`
  In-memory message-state helpers used by the runner.
- `events.py`
  Small event-emission wrapper so UI callbacks stay out of the loop logic.
- `response.py`
  Normalization helpers for streamed chunks and tool-call serialization.
- `tool_registry.py`
  Builds the list of model-visible tool schemas from the MCP client plus any policy-defined pseudo-tools.
- `tool_dispatch.py`
  Executes tool calls through the MCP client or through orchestration-registered special handlers.

## Relationship to adjacent directories

- `inference/` supplies the streaming chat client.
- `orchestration/` provides prompts, policies, and special tool handlers.
- `context/` provides the message state object that the loop mutates.

This package should not know concrete tool names like `delegate_agent`, and it should not know anything about SQLite or web/Discord transport details.
