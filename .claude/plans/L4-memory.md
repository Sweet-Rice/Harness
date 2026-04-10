# Layer 4: Memory

## Purpose
Without memory, every conversation starts from zero. Memory gives the agent continuity — it remembers user preferences, past decisions, and accumulated knowledge across sessions. Different memory tiers serve different retrieval depths.

## Status
NOT STARTED

## What Exists
- SQLite conversation history in `harness/utils/context.py` — this is conversation persistence (L5), not memory. Messages are stored verbatim; there's no semantic retrieval, summarization, or injection into new sessions.

## Memory Tiers

| Tier | Depth | Use Case | Retrieval Method |
|------|-------|----------|------------------|
| Model weights | Casual | General conversation, world knowledge | Native inference |
| Short-term | Shallow | Current conversation window | Message history in context |
| Long-term | Medium | Facts, preferences, past decisions | Basic semantic search (RAG) |
| Episodic | Deeper | Session summaries, what happened when | Deeper semantic search with context |
| **Technical** | **Deep** | **Highly nuanced retrieval for technical tasks** | **Semantic graph traversal** |

## What's Planned

### Short-term Memory
The conversation window itself. Already exists implicitly in the message history passed to each `ollama.chat()` call. No changes needed.

### Long-term Memory (Vector Store)
- **Fact store**: Key-value facts, preferences, and decisions stored as embeddings. Semantically searchable.
  - Location: `harness/memory/facts.py` (new)
  - Depends on: L5 (persistent context storage), vector store library
- **Injection into system prompt**: Relevant memories retrieved at conversation start and injected as context.
  - Location: integrated into `harness/utils/prompts.py`
  - Depends on: fact store

### Episodic Memory
- **Session summaries**: Auto-generated summaries of past conversations, stored for retrieval.
  - Location: `harness/memory/episodes.py` (new)
  - Depends on: L5, L1 (summarization model call)
- **What happened last time**: When the user returns, the agent can recall what was discussed and decided.

### User Model
- **Structured knowledge about the user**: Role, expertise, preferences, communication style. Updated incrementally as the agent learns.
  - Location: `harness/memory/user_model.py` (new)
  - Depends on: L5

### Technical Memory (Semantic Graph Traversal)

**This is not RAG. It is a goal-anchored, heuristic, disk-backed semantic graph traversal system where the LLM functions purely as a branch-selection oracle.**

#### 1. Storage Layer

Each node is a **folder** containing:
- JSON metadata file (id, parent_id, children_ids, relative_ids, embedding, token constraints)
- Two text fields: **summary** and **content**
- Optional children folders

**Two-field model:**
| Field | Size | Embedded? | When Read | Purpose |
|-------|------|-----------|-----------|---------|
| `summary` | Token-bounded (50–200) | Yes — drives scoring | Candidate selection (preloaded in RAM) | Discriminative label for traversal |
| `content` | Unbounded | Never | On node visit only (disk read) | Full technical depth |

The summary must be discriminative enough for the scoring function to differentiate nodes. The content can be as deep as needed — it's only read once on visit and never affects traversal performance. Embeddings are computed from summaries only.

The directory hierarchy encodes parent-child relationships. Topology is redundantly stored in metadata for in-memory reconstruction without filesystem traversal.

See [L4-technical_example.md](L4-technical_example.md) for concrete node schemas and examples.

- Location: `harness/memory/technical/` (node tree on disk)
- Location: `harness/memory/graph.py` (graph engine — new)
- Depends on: L5 (persistence abstraction), embedding model

#### 2. Initialization (Orchestrator Startup)

Walk entire directory tree. Load into two in-memory structures:

**Embedding Lookup Table**
```
node_id → embedding vector
```
Used only for similarity scoring.

**Graph Index**
```
node_id → {
    parent_id,
    children_ids,
    relative_ids,
    absolute_path
}
```
Enables traversal decisions without disk access. Disk is only accessed when node content is needed.

#### 3. Runtime Objects

| Object | Purpose | Location |
|--------|---------|----------|
| **E₀** (Original Prompt Embedding) | Global objective anchor. Computed once at start. | In memory |
| **Attention File** | Growing text file: visited summaries, extracted details, reasoning trace. Recomputed as Eₐ after each visit. Encodes trajectory state. | Disk-backed or memory |
| **Blacklist** | Visited node IDs. Prevents re-expansion, cycles, oscillation. | In memory (set) |
| **Priority Queue** | Candidate nodes ranked by score: `(node_id, score)`. The search frontier. | In memory |

#### 4. Retrieval / Expansion Cycle

Each iteration follows **strict isolation**:

**4a. Candidate Generation**
From current node: children, relatives, parent (optional upward). Remove blacklisted nodes.

**4b. Scoring**
```
Score(n) = α · sim(E₀, Eₙ) + β · sim(Eₐ, Eₙ)
```
- `sim` = cosine similarity
- `α` prevents global drift (anchors to original goal)
- `β` preserves local coherence (follows the thread)
- Insert scored candidates into priority queue

**4c. LLM Decision Phase**
LLM receives ONLY:
- Original prompt
- Current node summary
- Attention file
- Candidate options (IDs + summaries)

LLM answers: "What do you need more on?"
Options: specific child, relative, parent, nothing, unrelated.

**The LLM does not fetch. It only selects.**

**4d. Context Reset**
Before each expansion, LLM context contains ONLY: original prompt + current node + attention file. No historical chain. All long-term state is external.

**4e. Node Visit**
1. Read `content` field from disk (not summary — the full depth)
2. Append structured summary (derived from content) to attention file
3. Add node ID to blacklist
4. Recompute Eₐ
5. Return control to orchestrator

#### 5. Termination

Stop when:
- LLM chooses "Nothing"
- Semantic convergence (confidence threshold met)
- Priority queue exhausted
- Token budget satisfied

Final output: original prompt + compressed attention file. Minimal necessary detail injected into orchestrator context.

#### 6. Drift Prevention

| Mechanism | What It Prevents |
|-----------|------------------|
| E₀ anchor in scoring | Global drift from original goal |
| Blacklist | Loops and oscillation |
| Context reset per iteration | Compounding hallucination |
| Token bounds on summaries | Context bloat |
| Dual similarity scoring (α + β) | Local-only greediness |

#### 7. Performance

- Embeddings + topology fully in RAM — disk only on node visit
- Per iteration: O(k) similarity computations + 1 embedding recomputation + 1 LLM inference (k = candidate neighbors)

#### 8. Failure Modes

| Failure | Consequence |
|---------|-------------|
| Over-compression of attention file | Loss of critical nuance |
| Embedding noise | Incorrect prioritization |
| Poor α/β tuning | Too global → shallow; too local → drift |
| Underspecified prompt | E₀ too broad → inefficient exploration |

## Architecture (Full Memory System)

```
New Conversation
  │
  ▼
Memory Retrieval (tiered)
  ├─ Long-term: query fact store (basic semantic search)
  ├─ Episodic: load recent session summaries
  ├─ User model: load structured user knowledge
  ├─ Technical: semantic graph traversal (when task requires deep retrieval)
  │
  ▼
System Prompt Assembly
  ├─ Base system prompt
  ├─ + Relevant facts
  ├─ + Recent episodes
  ├─ + User model
  ├─ + Technical context (compressed attention file)
  │
  ▼
Orchestrator LLM (enriched context)
  │
  ▼
Post-conversation
  ├─ Extract new facts → fact store
  ├─ Generate episode summary → episodes
  ├─ Update user model if new info learned
  └─ Update technical graph if new technical knowledge acquired
```

## Key Decisions
- **Technical memory is not RAG**: It is controlled best-first search over a hierarchical semantic index. The LLM is a local decision oracle, not a retrieval engine.
- **LLM never owns global state**: All structure, memory, and control flow reside in the orchestrator and external data structures.
- **Context isolation per iteration**: Prevents compounding hallucination — the core reliability guarantee.
- **Orchestrator decides retrieval depth**: The orchestrator always chooses which memory tier to query. A dedicated reasoning tool in the tooling loop handles this decision — no hardcoded routing rules. This is tier selection as tool-as-abstraction.
- **Graph construction spec**: The ingestion pipeline (how nodes are created, chunked, summarized, embedded) is specced separately — see `plans/technical-memory-ingestion.md`.

## Open Questions
- **Vector store / embedding model**: What generates embeddings? Dedicated small model or reuse inference model?
- **Graph construction / ingestion**: How do technical memory nodes get created? Static analysis of source files? Agent observation during tasks? Manual curation? This is a substantial subsystem that needs its own design.
- **Attention file compression**: When does the attention file get compressed during traversal? Rolling compression per N steps, or only at termination? The text_tool from L6 could serve this purpose.
- **α/β tuning**: Static values or adaptive? Could adjust based on traversal depth (more global weight early, more local weight deep).
- **Privacy**: Should there be a way for users to view, edit, and delete stored memories across all tiers?
- **Memory capacity management**: Compression, eviction, summarization strategies for growing stores.
- ~~**Tier selection**~~: Resolved — orchestrator decides via reasoning tool. No hardcoded routing.
