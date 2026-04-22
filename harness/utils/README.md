# `harness/utils`

This directory is the shared utility layer for the harness. The goal of the recent refactor is to keep the public entrypoints here thin and push real behavior into focused subpackages.

## Adjacent files

- `llm.py`
  Compatibility entrypoint for the main tool-calling loop. It should stay small and forward into `loop/` plus `orchestration/`.
- `agents.py`
  Compatibility wrapper for delegation behavior. The real delegation logic now lives in `orchestration/delegation.py`.
- `config.py`
  Central configuration surface for model roles, loop limits, and shared runtime settings.
- `prompts.py`
  Compatibility wrapper for the old prompt import path. Prompt ownership now lives in `orchestration/prompts.py`.
- `__init__.py`
  Package marker for utility imports.

## Adjacent subdirectories

- `context/`
  In-memory conversation state, typed thread/message records, and the compatibility `ConversationManager` surface.
- `inference/`
  Provider-facing model access. This is the only place that should know how to talk to Ollama or any future backend.
- `loop/`
  The generic MCP-first conversation engine: streaming, message mutation, tool registry, and tool dispatch.
- `orchestration/`
  Harness-specific policy such as prompts, delegation, and default loop behavior.
- `persistence/`
  Storage interfaces and SQLite-backed thread/message persistence.
- `providers/`
  Legacy placeholder from before the refactor. New provider work should go in `inference/`.

## Direction

If a change is about "how the harness behaves," it usually belongs in one of the subdirectories.
If a change is about "keeping old imports working," it usually belongs in one of the thin wrapper files here.
