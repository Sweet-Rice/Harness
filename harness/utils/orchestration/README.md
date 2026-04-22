# `orchestration`

This package holds harness-specific policy layered on top of the generic loop engine.

## Files

- `__init__.py`
  Public import surface for orchestration policy helpers.
- `prompts.py`
  System prompts for orchestrator, delegated sub-agents, and simple chat.
- `policy.py`
  Builds the default conversation policy: model role, loop limits, prompt, special tools, and special handlers.
- `delegation.py`
  Implements the `delegate_agent` pseudo-tool and the restricted sub-agent execution path.
- `skills.py`
  Shared skill trigger layer used by explicit client commands and orchestrator-owned pseudo-tools.
- `plan_model.py`
  Typed plan-domain models plus the strict markdown parser/renderer for canonical plan files.
- `plan_state.py`
  Bridges canonical file-backed plan state to active orchestrated runs while keeping conversation threads as interface mirrors.

## Relationship to adjacent directories

- Uses `inference/` indirectly through the registry and shared model roles.
- Registers special tool handlers that are consumed by `loop/`.
- Supplies default prompt behavior to `context/` and compatibility wrappers like `prompts.py`.

When behavior is specific to "how this harness should operate," it probably belongs here rather than in `loop/`.
