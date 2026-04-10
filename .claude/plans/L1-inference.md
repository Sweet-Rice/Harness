# Layer 1: Inference Abstraction

## Purpose
A single interface for talking to any model. All downstream code talks to this interface, never to a specific provider. This is foundational — everything else depends on it.

## Status
PARTIAL

## What Exists
- `ollama.AsyncClient().chat()` calls throughout the codebase — hardcoded to Ollama
- Model name `qwen3-coder` hardcoded in tool files (`plan.py`, `output.py`, `review.py`)
- Streaming support via `stream=True` in `harness/utils/llm.py:_stream()`
- Thinking mode toggle via global `_thinking` flag in `harness/utils/llm.py`
- `harness/tools/thinking.py` — enable/disable thinking tools

## What's Planned
- **Abstract model interface**: A provider-agnostic class/protocol that wraps `chat()`, `stream()`, and model configuration. Swapping Ollama for another backend should require changing one config value, not editing tool files.
  - Location: `harness/utils/inference.py` (new)
  - Depends on: nothing (foundational)
- **Model registry/config**: Named model profiles (e.g., `orchestrator: gemma4`, `coder: qwen3-coder`, `reviewer: gemma4`) loaded from config.
  - Location: `harness/config.py` or similar (new)
  - Depends on: abstract interface
- **Per-task model routing**: Sub-agents and tools can request a model by role (e.g., "give me the coder model") rather than by name.
  - Location: integrated into inference abstraction
  - Depends on: model registry

## Architecture
```
Tool / Orchestrator
  │
  ▼
InferenceClient (abstract interface)
  │
  ├─ OllamaProvider (current backend)
  ├─ Future: AnthropicProvider, OpenAIProvider, etc.
  │
  ▼
Model Registry (config-driven)
  ├─ orchestrator → gemma4
  ├─ coder → qwen3-coder
  └─ reviewer → gemma4
```

All existing `ollama.chat()` calls in `plan.py`, `output.py`, `review.py`, and `llm.py` would be replaced with calls to the abstract interface.

## Key Decisions
- **Ollama as initial backend**: Local inference, Apache 2.0 models, no API costs
- **Gemma 4 as primary orchestrator**: Strong instruction following, clean structured outputs, less verbose
- **Qwen 3 Coder for code tasks**: Better function calling and code generation, hybrid chain-of-thought
- **Both Apache 2.0**: No licensing constraints

## Open Questions
- Should the abstraction support multiple simultaneous providers (e.g., Ollama for local + Claude API for hard tasks)?
- How to handle provider-specific features (e.g., Ollama's thinking mode vs. Claude's extended thinking)?
- Should model selection be static config or dynamic (auto-select based on task complexity)?
