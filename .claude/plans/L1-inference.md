# Layer 1: Inference Abstraction

## Purpose

A single interface for talking to any model. All downstream code should talk to that interface, never to a provider SDK directly.

## Status

PARTIAL

## What Exists

- `harness/utils/inference/base.py`
  Shared stream chunk shape and inference client contract
- `harness/utils/inference/ollama.py`
  Current Ollama-backed implementation
- `harness/utils/inference/registry.py`
  Config-driven role lookup for `orchestrator`, `delegate`, and `chat`
- `harness/utils/config.py`
  Central model/provider settings
- Web, Discord, the shared loop, and explicit skills all go through the inference layer

## What's Planned

- **Broader provider support**
  The abstraction should be able to grow beyond Ollama without changing loop/orchestration callers.
- **Richer model roles**
  Add explicit roles such as `coder`, `reviewer`, and future memory/verification roles instead of overloading `chat`.
- **Provider capability handling**
  Normalize provider-specific features such as thinking/reasoning modes without leaking provider assumptions upward.
- **Per-task model routing**
  Delegation, skills, review passes, and future orchestration tools should request models by role rather than by provider-specific model name.

## Architecture

```
Tool / Orchestrator / Skill
  │
  ▼
Inference Registry
  │
  ▼
Inference Client (abstract)
  │
  ├─ Ollama (current)
  ├─ Future: Anthropic
  └─ Future: OpenAI / others
```

## Key Decisions

- Keep provider construction inside `utils/inference/`
- Model selection is role-based, not call-site hardcoded
- Loop and orchestration code should not import provider SDKs directly

## Open Questions

- Should multiple providers be usable simultaneously for different roles?
- How should provider-specific reasoning modes map onto one common interface?
- Should model-role selection stay static config, or become dynamic later?
