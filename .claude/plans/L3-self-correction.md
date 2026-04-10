# Layer 3: Self-Correction

## Purpose
The harness validates outputs before passing them back. If the model emits broken output, retry. If a tool call fails, feed the error back. After multi-step tasks, run a verification pass. This is the cheapest way to improve reliability without changing the model.

## Status
PARTIAL

## What Exists
- **Plan review**: `plan_review(plan, intent)` in `harness/tools/plan.py` — LLM evaluates plan against intent, returns VERDICT: PASS/FAIL with explanation
- **Output review**: `output_review(output, plan, intent)` in `harness/tools/output.py` — LLM evaluates output against plan + intent, returns VERDICT: PASS/FAIL
- **Orchestrator retry**: The main loop in `harness/utils/llm.py` passes FAIL verdicts back to the orchestrator, which decides whether to retry
- **MAX_TOOL_ROUNDS = 15**: Safety cap on main loop iterations (`harness/utils/llm.py`)
- **MAX_INNER_ROUNDS = 10**: Safety cap on output() inner loop (`harness/tools/output.py`)

## What's Planned
- **JSON schema validation**: Validate tool call arguments and return values against expected schemas before processing. Catch malformed tool calls early instead of letting them propagate.
  - Location: `harness/utils/validation.py` (new)
  - Depends on: nothing
- **Tool call error recovery**: When a tool call fails (exception, timeout, bad output), capture the error, feed it back to the model with context, and let it retry or adapt. Currently errors may crash or get swallowed.
  - Location: integrated into `harness/utils/llm.py` main loop
  - Depends on: nothing
- **Multi-pass verification**: After a complex task completes, run a separate verification pass where the model reviews its own work holistically (not just output vs plan, but "does this actually solve the user's problem?").
  - Location: `harness/tools/verify.py` (new) or extension of output_review
  - Depends on: L1 (may want a different model for verification)
- **Structured output enforcement**: For tool calls that must return specific formats (JSON, PASS/FAIL verdicts), parse and validate the structure, retrying on malformed output.
  - Location: utility function in validation module
  - Depends on: nothing

## Architecture
```
Tool Call
  │
  ├─ Pre-validation (schema check on arguments)
  │
  ▼
Tool Execution
  │
  ├─ Success → Post-validation (schema check on return value)
  │              │
  │              ├─ Valid → return to orchestrator
  │              └─ Invalid → retry with error context
  │
  └─ Failure → Error recovery
                 │
                 ├─ Feed error + context back to model
                 └─ Model retries or adapts approach
```

Review tools (plan_review, output_review) sit at a higher level — they validate semantic correctness, not structural correctness.

## Key Decisions
- **LLM-based review over rule-based**: Reviews use `ollama.chat()` calls rather than hardcoded validation rules — more flexible, catches semantic issues
- **PASS/FAIL verdicts**: Binary outcome with explanation text — simple for the orchestrator to act on
- **Orchestrator decides retries**: The main loop doesn't hardcode retry logic; it passes FAIL results back and lets the model decide

## Open Questions
- How many retries before giving up? Currently no explicit limit beyond MAX_TOOL_ROUNDS
- Should verification use a different model than the one that produced the output (to avoid self-confirmation bias)?
- What's the right granularity for JSON schema validation — per-tool schemas or a generic structure check?
