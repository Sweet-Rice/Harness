# Layer 1: Inference Abstraction

## Purpose
A single interface for talking to any model. All downstream code talks to this interface, never to a specific provider. This is foundational — everything else depends on it.

## Status
DONE

## What Exists

### Abstract Interface (`harness/utils/inference.py`)
- **InferenceProvider** ABC with `chat()` and `stream()` methods
- **InferenceClient** — entry point for all inference. Resolves roles to providers.
  - `chat(role, messages, tools, think)` → `InferenceResult`
  - `stream(role, messages, tools, think)` → `AsyncIterator[StreamChunk]`
- Provider-agnostic data types: `ToolCallInfo`, `StreamChunk`, `InferenceResult`

### Ollama Provider (`harness/utils/providers/ollama.py`)
- `OllamaProvider` implementing `InferenceProvider`
- Wraps `ollama.AsyncClient` — handles streaming, tool call extraction, thinking
- Provider-specific details (tool call format, thinking tokens) encapsulated here

### Config (`harness/config.py`, `harness.toml`)
- TOML-based config with `[providers]` and `[models]` sections
- Role-based model routing: orchestrator → qwen3.5, coder → qwen3-coder, reviewer → qwen3.5
- `HarnessConfig` / `ProviderConfig` / `ModelConfig` dataclasses
- Per-model options: `think` toggle, custom `options` dict

### Integration
- `harness/utils/llm.py` uses `InferenceClient` exclusively — no direct ollama calls
- Shared instance via `get_inference()` — available to any module that needs LLM access
- Agent delegation uses roles to route to different models (orchestrator role for planner agent, coder role for coder agent)

## Architecture
```
Supervisor / Agent Loop
  │
  ▼
InferenceClient (role → provider + model)
  │
  ├─ OllamaProvider (current)
  ├─ Future: AnthropicProvider, OpenAIProvider, etc.
  │
  ▼
harness.toml
  ├─ orchestrator → ollama / qwen3.5
  ├─ coder → ollama / qwen3-coder
  └─ reviewer → ollama / qwen3.5
```

## Key Decisions
- **Ollama as initial backend**: Local inference, Apache 2.0 models, no API costs
- **Qwen 3.5 as orchestrator**: Strong instruction following, good for delegation
- **Qwen 3 Coder for code tasks**: Better function calling and code generation
- **Static config**: Roles mapped to models in TOML, not dynamic auto-selection
- **Think toggle per model config**: The `think` field in ModelConfig, no runtime toggle tool (yet)

## What's Remaining
- Add more providers (Anthropic, OpenAI) when needed — just implement `InferenceProvider`
- Runtime thinking toggle tool (old `thinking.py` was deleted in refactor)

## Open Questions
- Should the abstraction support multiple simultaneous providers (e.g., Ollama for local + Claude API for hard tasks)?
- How to handle provider-specific features (e.g., Ollama's thinking mode vs. Claude's extended thinking)?
