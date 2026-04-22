# Layer 6: Planning & Orchestration

## Purpose

The orchestrator receives tasks, writes plans, delegates to sub-agents, and manages execution. State should live in plan files, not in chat history. The orchestrator delegates; it does not do work directly.

## Status

PARTIAL

## What Exists

### Generic Loop

- `harness/utils/llm.py`
  Thin compatibility entrypoint into the shared loop
- `harness/utils/loop/runner.py`
  Generic async tool-calling loop
- `harness/utils/loop/events.py`
  Streaming event emission

The loop remains generic and does not hardcode orchestration phases.

### Orchestration Surfaces

- `harness/utils/orchestration/prompts.py`
  Orchestrator, delegate, and chat prompts
- `harness/utils/orchestration/policy.py`
  Builds client- and mode-aware orchestration policy
- `harness/utils/orchestration/delegation.py`
  Restricted sub-agent pseudo-tool
- `harness/utils/orchestration/skills.py`
  Shared skill trigger layer
- `harness/utils/orchestration/plan_state.py`
  Plan-first run/session bridge and plan-state synchronization service

### Current Event Surfaces

| Event | Purpose |
|-------|---------|
| `stream_start` | Begin streamed assistant output |
| `stream_token` | Incremental token output |
| `stream_thinking` | Thinking/reasoning token output |
| `stream_end` | End of streamed assistant output |
| `log` | Debug/progress side-channel |
| `message` | Final assistant message |

### Current Plan-First Cutover

- Global orchestrated web threads now create/load a plan workspace
- Plan files (`ctrl`, `in_use`, diffs) are canonical for orchestrated task state
- Thread history remains the UI/session mirror and replay surface

## What's Planned

### Richer Plan File Versioning

Deepen the ctrl/in_use/diff model so every meaningful orchestration transition is explicit and queryable.

### Sub-Agent Delegation

The orchestrator should create sub-agents with:
- task-specific prompts
- restricted tools
- potentially different model roles
- progress that flows back into the canonical plan file

### Target Control Flow

```
User message
  │
  ▼
Orchestrator
  │
  ├─ loads canonical plan state
  ├─ updates in_use plan
  ├─ delegates focused work
  ├─ records diffs as state changes
  ├─ runs summarization/verification passes
  └─ mirrors useful progress back into thread history
```

### text_tool (Summarization)

A dedicated summarization pass should read accumulated diffs, compress progress, and help infer next steps without burning the orchestrator's main planning capacity.

### Context File Tree

A persistent file-context structure should give agents working memory about the project and integrate with plan-state progression.

## Key Decisions

- The loop stays generic; orchestration behavior lives above it
- Plan state is canonical for orchestrated work
- Conversation threads are transport, replay, and interface state
- The orchestrator should delegate rather than directly own every detailed action

## Open Questions

- How should sub-agents report progress back: diffs, structured status updates, or both?
- Should sub-agents be able to spawn sub-agents?
- How is “step complete” represented inside the plan workspace?
- Should summarization run after every step or only at selected checkpoints?
