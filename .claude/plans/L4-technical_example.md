Below is a concrete, low-level snapshot of how the technical memory system looks in practice across three layers:

- Node JSON (disk representation)
- Hierarchy (tree structure)
- In-memory node structure (orchestrator view)

No code constructs, just structural schemas.

## 1. Sample Node JSON (Disk-Level)

Each node is self-contained metadata + two text fields: `summary` (short, embedded, used for scoring) and `content` (long, read on visit, never embedded).

Example: `/root/networking/tcp_congestion_control/node.json`
```json
{
  "id": "tcp_cc_001",
  "parent_id": "networking_tcp",
  "absolute_path": "/root/networking/tcp_congestion_control",

  "summary": "TCP congestion control manages network traffic by adjusting sending rate based on perceived network congestion signals such as packet loss and latency increases.",

  "content": "TCP congestion control is a set of algorithms that prevent network collapse by regulating how fast a sender injects packets into the network.\n\nThe core mechanism is the congestion window (cwnd), a sender-side variable that limits the number of unacknowledged bytes in flight. The effective sending rate is min(cwnd, rwnd) / RTT, where rwnd is the receiver's advertised window.\n\nThree phases govern cwnd behavior:\n\n1. Slow Start: cwnd starts at 1 MSS (or IW per RFC 5681). Each ACK doubles cwnd — exponential growth. This continues until cwnd reaches ssthresh (slow start threshold), at which point the sender transitions to congestion avoidance. If a loss event occurs during slow start, ssthresh is set to cwnd/2 and the response depends on the variant.\n\n2. Congestion Avoidance: cwnd increases by ~1 MSS per RTT (additive increase). This is the steady-state probing phase. The sender linearly probes for available bandwidth until a loss signal indicates the network is saturated.\n\n3. Loss Response: On triple duplicate ACK (fast retransmit), most variants halve cwnd and enter fast recovery. On RTO timeout, cwnd resets to 1 MSS and re-enters slow start — the most aggressive response.\n\nVariants differ primarily in loss response and bandwidth estimation:\n- Reno: AIMD (additive increase, multiplicative decrease). Halves cwnd on loss. Simple but underperforms on high-BDP paths.\n- CUBIC: Default in Linux. Uses a cubic function of time since last loss to set cwnd. More aggressive recovery than Reno on long-fat networks.\n- BBR: Model-based, not loss-based. Estimates bottleneck bandwidth and RTprop to set cwnd and pacing rate. Decouples congestion detection from packet loss.\n\nECN (Explicit Congestion Notification) allows routers to signal congestion before loss occurs, enabling preemptive cwnd reduction. Supported as an extension across all variants.",

  "token_bounds": {
    "min_summary_tokens": 50,
    "max_summary_tokens": 200
  },

  "embedding": [0.012, -0.44, 0.883, "..."],

  "children_ids": [
    "tcp_slow_start",
    "tcp_congestion_avoidance",
    "tcp_fast_retransmit"
  ],

  "related_ids": [
    "udp_protocols",
    "network_qos_models"
  ],

  "metadata": {
    "created": "2026-04-09T12:00:00Z",
    "version": 1,
    "blacklisted": false
  }
}
```

### Two-Field Model

| Field | Size | Embedded? | When Read | Purpose |
|-------|------|-----------|-----------|---------|
| `summary` | Token-bounded (50–200) | Yes — drives scoring | Candidate selection (in RAM) | Discriminative label for traversal |
| `content` | Unbounded | Never | On node visit only (disk read) | Full technical depth |

**Why two fields:**
- Traversal stays fast — scoring uses summary embeddings, small and preloaded in RAM
- Depth lives in content — visited nodes deliver real substance, not one-liners
- Attention file captures depth — post-visit summaries can pull from full content
- Granularity problem solved — summary must be discriminative enough for scoring; content can be as deep as needed

### Example Child Node
```json
{
  "id": "tcp_slow_start",
  "parent_id": "tcp_cc_001",
  "absolute_path": "/root/networking/tcp_congestion_control/tcp_slow_start",

  "summary": "TCP slow start is a phase where the congestion window increases exponentially from 1 MSS until reaching ssthresh or encountering loss.",

  "content": "Slow start is the initial phase of TCP congestion control, designed to quickly discover available bandwidth without prior knowledge of network capacity.\n\nMechanism: The sender initializes cwnd to IW (initial window, typically 10 MSS per RFC 6928). For each ACK received, cwnd increases by 1 MSS. Since each RTT roughly ACKs all outstanding segments, this produces exponential growth — cwnd doubles every RTT.\n\nExit conditions:\n1. cwnd >= ssthresh → transition to congestion avoidance (linear probing)\n2. Packet loss detected → loss response (variant-dependent)\n3. ECN-CE received → preemptive reduction\n\nOn first connection, ssthresh is typically initialized to a large value (effectively infinity), so slow start runs until first loss. After a loss event, ssthresh is set to cwnd/2, meaning subsequent slow start phases exit earlier.\n\nEdge cases:\n- Idle restart: RFC 5681 recommends resetting cwnd after an idle period exceeding RTO, re-entering slow start. Not all implementations comply.\n- Application-limited: If the application doesn't saturate cwnd, slow start may never trigger loss, leading to an inflated cwnd that doesn't reflect actual network capacity.",

  "token_bounds": {
    "min_summary_tokens": 30,
    "max_summary_tokens": 150
  },

  "embedding": [0.01, -0.31, 0.91, "..."],

  "children_ids": [],
  "related_ids": ["congestion_window", "ssthresh"]
}
```

## 2. Hierarchy Structure (Tree View)

Logical organization on disk and in-memory:

```
/root
 ├── networking
 │    ├── tcp
 │    │    ├── tcp_congestion_control (tcp_cc_001)
 │    │    │    ├── tcp_slow_start
 │    │    │    ├── tcp_congestion_avoidance
 │    │    │    ├── tcp_fast_retransmit
 │    │    │
 │    │    ├── tcp_handshake
 │    │    ├── tcp_header_format
 │    │
 │    ├── udp
 │    │    ├── udp_datagram_structure
 │    │    ├── udp_use_cases
 │
 ├── systems
 │    ├── scheduling
 │    ├── memory_management
 │
 ├── ai
      ├── embeddings
      ├── transformer_attention
      ├── retrieval_systems
```

## 3. Graph Extension Layer (Non-tree edges)

Related links are lateral semantic cross-links stored only in JSON, not as directory relationships:

```
tcp_congestion_control
   ↔ network_qos_models
   ↔ congestion_window_control
   ↔ packet_loss_detection
```

## 4. In-Memory Node Structure (Orchestrator View)

Loaded at startup. Each node becomes a lightweight object:

```
Node[tcp_cc_001]:

  Structural Fields
    parent_id      → networking_tcp
    children_ids   → [slow_start, avoidance, fast_retransmit]
    related_ids    → [udp_protocols, network_qos_models]
    absolute_path  → /root/networking/tcp/congestion_control
    summary        → "TCP congestion control manages..."

  Embedding Field
    embedding_vector → [ ... ]

  Runtime Fields (not on disk)
    visited: false
    priority_score: float
    depth: int
```

Stored in centralized lookup tables:
- `embedding_table[tcp_cc_001] → vector`
- `graph_index[tcp_cc_001] → {parent, children, related, path}`
- `summary_table[tcp_cc_001] → summary text` (for candidate display to LLM)

**Content is NOT loaded at startup.** Read from disk only on visit.

## 5. Traversal Using Two-Field Model

```
Step 1: Candidate Expansion
  From current node → children_ids, related_ids, parent_id
  Filter out blacklisted nodes

Step 2: Scoring (uses summary embeddings only)
  Score(n) = α · sim(E₀, Eₙ) + β · sim(Eₐ, Eₙ)
  Insert into priority queue

Step 3: LLM Selection (sees summaries, not content)
  LLM receives: original prompt + current node content + attention file + candidate summaries
  LLM selects which candidate to visit

Step 4: Node Visit (reads content from disk)
  Load content field from disk
  Append structured summary (derived from content) to attention file
  Recompute Eₐ
  Add to blacklist

Step 5: Repeat or terminate
```

## Node Schema Reference

```
Node {
    id: string
    path: string
    summary: string          # short, embedded, token-bounded
    content: string          # long, unbounded, disk-only
    embedding: vector        # computed from summary
    parent_id: string
    children_ids: string[]
    related_ids: string[]
    token_bounds: {
        min_summary_tokens: int
        max_summary_tokens: int
    }
    metadata: {
        created: datetime
        version: int
        blacklisted: bool
    }
}
```
