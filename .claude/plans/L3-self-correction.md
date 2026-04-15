# Layer 3: Self-Correction

## Purpose
The harness validates outputs before passing them back. If the model emits broken output, retry. If a tool call fails, feed the error back. After multi-step tasks, run a verification pass. This is the cheapest way to improve reliability without changing the model.

## Status
MINIMAL

## What Exists
- **Tool call error recovery**: The main loop in `harness/utils/llm.py` catches tool call exceptions, feeds error messages back to the model as tool responses, and continues the loop. The model can retry or adapt.
- **`max_tool_rounds`**: Safety cap on loop iterations (configurable in `harness.toml`, default 15). Prevents infinite loops.
- **Orchestrator review**: The system prompt instructs the orchestrator to review agent output via the plan file before presenting results. This is prompt-based, not harness-enforced.
- **Self-contained agent validation**: Agent system prompts (in `harness/utils/agents.py`) instruct agents to validate their own work (e.g., planner checks for missing steps).

## What Was Deleted in Refactor
- `plan_review(plan, intent)` — LLM-powered plan validation with VERDICT: PASS/FAIL
- `output_review(output, plan, intent)` — LLM-powered output validation with VERDICT: PASS/FAIL
- Inner loop safety cap (`MAX_INNER_ROUNDS = 10`) — no inner loop exists anymore

## What's Planned
- **JSON schema validation**: Validate tool call arguments and return values against expected schemas before processing.
  - Location: `harness/utils/validation.py` (new)
  - Depends on: nothing
- **Multi-pass verification**: After a complex task completes, run a separate verification pass. Could be a dedicated "reviewer" agent that uses the reviewer role (different model).
  - Location: new agent in `harness/utils/agents.py` or `harness/tools/verify.py`
  - Depends on: L6 agent infrastructure (done)
- **Structured output enforcement**: Parse and validate tool call JSON structure, retry on malformation.
  - Location: utility function in validation module
  - Depends on: nothing

## Architecture
```
Tool Call (in loop)
  │
  ├─ Success → result appended to messages
  │
  └─ Failure → error message appended to messages
                 │
                 └─ Model sees error, retries or adapts

Semantic Validation (prompt-based):
  Orchestrator reviews agent output via plan file
  Agents self-validate per their system prompts

Future (harness-enforced):
  Pre-validation → schema check on args
  Post-validation → schema check on returns
  Multi-pass verification → reviewer agent
```

## Key Decisions
- **Prompt-based review**: The orchestrator is instructed to review agent results. Not harness-enforced yet.
- **Error recovery in loop**: Tool errors are caught and fed back — model decides how to respond.
- **Self-contained agents**: Each agent's system prompt includes validation instructions.

## Open Questions
- Should review be a separate agent (reviewer) or a harness-level check?
- How many retries before giving up? Currently only bounded by `max_tool_rounds`.
- Should verification use a different model than the one that produced the output (to avoid self-confirmation bias)?
- What's the right granularity for JSON schema validation — per-tool schemas or a generic structure check?
