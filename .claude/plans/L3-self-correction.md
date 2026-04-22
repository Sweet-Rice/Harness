# Layer 3: Self-Correction

## Purpose

The harness should validate and recover before returning bad work. If a tool call is malformed, catch it. If a tool fails, feed the failure back. If a complex task finishes, verify it with a separate pass.

## Status

PARTIAL

## What Exists

- Generic loop safety caps in `harness/utils/loop/runner.py`
- Shared tool dispatch and error surfacing in `harness/utils/loop/tool_dispatch.py`
- Structured message typing in `utils/context/models.py`, which already constrains message shape
- Explicit skill and delegation seams in `utils/orchestration/`, which can host future verification/review behaviors

## What's Planned

- **JSON/schema validation**
  Validate tool-call arguments and structured outputs before and after execution
- **Better tool error recovery**
  Feed tool failures back into the loop with enough context for retries or strategy changes
- **Verification pass**
  Add a dedicated review/verification behavior after complex work completes
- **Structured verdicts**
  Formalize review outputs such as `PASS` / `FAIL` or richer machine-parseable verdicts

The older `plan_review` / `output_review` idea still stands conceptually, but in the current architecture these should be implemented as orchestration-owned tools, skills, or verification services rather than assuming the old tool files already exist.

## Architecture

```
Model output
  │
  ├─ Structural validation
  │
  ▼
Tool dispatch / loop execution
  │
  ├─ Failure capture + retry context
  └─ Success path
         │
         ▼
  Optional verification pass
```

## Key Decisions

- Structural validation and semantic verification are separate concerns
- The loop should stay generic; higher-level review behavior belongs in orchestration
- Verification can use different model roles later to reduce self-confirmation bias

## Open Questions

- How many retries before giving up?
- Should verification always use a different model role?
- How strict should schema enforcement be for tool returns and review verdicts?
