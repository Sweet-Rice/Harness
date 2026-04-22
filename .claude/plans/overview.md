# t.ai — Roadmap

## Current State

A modular local LLM harness with:

- MCP server with auto-discovered tools via `TOOLS = [...]`
- Shared MCP-first loop under `harness/utils/loop/`
- Inference abstraction and model-role registry under `harness/utils/inference/`
- Orchestration policy, delegation, skill triggering, and early plan-state services under `harness/utils/orchestration/`
- Typed thread/message persistence under `harness/utils/persistence/`
- File-backed plan workspaces for orchestrated/global work
- Web and Discord interfaces sharing the same core loop, with client-aware tool policy
- Structured non-mutating write proposals for filesystem changes

The architecture already moved away from the old monolithic `llm.py`-centered design. The roadmap below keeps the same ideas, but all future work should land on the modular seams that now exist.

## Build Order

Following the stated principle: inference → persistence → tools → self-correction → memory → orchestration → interface expansion.

| Priority | Layer | Rationale |
|----------|-------|-----------|
| 1 | L1: Inference Abstraction | The abstraction exists, but all future provider/model-role work still depends on strengthening it |
| 2 | L5: Persistent Context Storage | Memory and plan-first orchestration both depend on durable abstractions |
| 3 | L2: Tool Use | Expand capability on top of the MCP-first tool and policy boundary |
| 4 | L3: Self-Correction | Harden validation, verification, and recovery around the generic loop |
| 5 | L4: Memory | Memory tiers depend on persistence and stable orchestration surfaces |
| 6 | L6: Orchestration | Plan-file-first orchestration, richer sub-agents, and summarization depend on L1 and L5 |
| 7 | L7: Interface | Voice/mobile can reuse the shared orchestrator once the core layers stabilize |

## Layer Dependencies

```
L1 (Inference) ──────────────────────────┐
  │                                       │
  ▼                                       ▼
L2 (Tools)          L5 (Persistence) → L6 (Orchestration)
  │                   │
  ▼                   ▼
L3 (Self-Correction)  L4 (Memory)
                                          │
                                          ▼
                                    L7 (Interface)
```

- L1 is foundational even though the first abstraction pass already landed
- L5 before L4 because memory needs a storage boundary
- L5 before L6 because plan workspaces and file context are persistent state
- L1 before L6 because richer delegation and verification need model-role routing
- L7 benefits from all prior layers being stable and shared

## Open Questions

- **Model selection:** Fixed role mapping or dynamic selection based on task type?
- **Vector store choice:** What backs long-term and episodic memory?
- **Plan file format:** Markdown-first forever, or structured sidecar metadata plus richer schemas later?
- **Tool permissions:** How far should per-client/per-agent allowlists go?
- **Dangerous action confirmation:** Which future tools require approval beyond write proposals?
