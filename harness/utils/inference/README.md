# `inference`

This package is the model-access seam. Anything that speaks directly to a model provider belongs here and should not leak into `llm.py`, `loop/`, or interface code.

## Files

- `__init__.py`
  Public import surface for the inference registry.
- `base.py`
  Shared protocol and stream-chunk shape used by the rest of the harness.
- `ollama.py`
  Ollama-specific client implementation. This is the only place that should instantiate `ollama.AsyncClient()`.
- `registry.py`
  Maps model roles like `orchestrator`, `delegate`, and `chat` to configured models and returns the active inference client.

## Relationship to adjacent directories

- `loop/` consumes the provider-agnostic interface defined here.
- `orchestration/` chooses model roles but should not construct provider clients itself.
- `config.py` provides the runtime settings used by the registry.

If you add another backend later, it should look like another sibling to `ollama.py`, not another direct import inside application code.
