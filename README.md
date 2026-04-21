# Harness

Harness is a local LLM harness built around an MCP-first execution loop. The main idea is that the model is only one part of the system: the harness provides tool access, orchestration rules, conversation state, persistence, and interface layers so the model can act more like an actual assistant instead of a bare text generator.

The current architecture is organized so the public entrypoints stay thin and the real behavior lives in focused subdirectories. The goal is to make future work land in the right place without turning the main loop into a dumping ground.

## Broad Directory Map

### `harness/`

The main Python package. This is the root of the runtime application.

- `server.py`
  Starts the FastMCP server and auto-registers tools from `harness/tools/`.
- `tools/`
  The MCP tool implementations the model can call.
- `utils/`
  Shared architecture code for loop execution, inference, orchestration, persistence, and compatibility wrappers.
- `web/`
  Web interface server and static frontend.
- `discord/`
  Discord bot interface and renderer.
- `conversations.db`
  SQLite conversation storage used by the current persistence layer.

### `harness/tools/`

Concrete MCP tools. These are the callable capabilities exposed to the model through the FastMCP server. Right now the visible implementation is small, but the directory is meant to grow as the harness gains more capabilities.

### `harness/utils/`

The shared core of the harness. This directory now holds the actual loop system, inference abstraction, orchestration policy, and storage boundaries. Thin compatibility wrappers also live here so older import paths keep working while the architecture evolves.

Main adjacent files:

- `llm.py`
  Thin compatibility entrypoint for the main tool-calling loop.
- `agents.py`
  Thin compatibility wrapper for delegated sub-agent behavior.
- `config.py`
  Shared configuration for models, limits, and runtime settings.
- `prompts.py`
  Compatibility wrapper for the default orchestrator system prompt.

Main adjacent subdirectories:

- `context/`
  In-memory conversation state and the compatibility `ConversationManager`.
- `inference/`
  Provider-facing model access.
- `loop/`
  Generic MCP-first conversation engine.
- `orchestration/`
  Harness-specific prompts, policy, and delegation behavior.
- `persistence/`
  Durable storage interfaces and SQLite-backed repositories.
- `providers/`
  Legacy placeholder from an earlier design. New provider work should go in `inference/`.

### `harness/web/`

The browser-facing interface.

- `server.py`
  Runs the HTTP and WebSocket server for the web UI.
- `static/`
  Browser assets, currently centered around the HTML frontend.

### `harness/discord/`

The Discord interface.

- `bot.py`
  Main Discord runtime and message handling.
- `renderer.py`
  Streaming-friendly response rendering for Discord.
- `__main__.py`
  Small module entrypoint so `python -m harness.discord` works cleanly.

## Broad Data Flow

At a high level, the harness works like this:

1. A user sends input through an interface such as the web UI or Discord.
2. The interface builds or loads conversation state.
3. The shared loop runs with an orchestration policy and an inference client.
4. The loop asks the MCP client for available tools and passes those tool schemas into the model.
5. The model either returns plain text or emits tool calls.
6. Tool calls are dispatched through the MCP client or through orchestration-owned handlers such as delegation.
7. Tool results are appended back into conversation state.
8. Once the model returns a final assistant message, the interface streams it to the user and optionally persists the updated conversation.

In short: interface -> state -> loop -> inference/tool calls -> updated state -> interface output -> persistence.

## In-Depth Architecture

### 1. Entry Points And Surfaces

The repo has three main runtime entrypoints:

- `python -m harness.server`
  Starts the FastMCP server that exposes tools.
- `python -m harness.web.server`
  Starts the web UI server.
- `python -m harness.discord`
  Starts the Discord bot.

The key design choice is that interfaces should not each invent their own architecture. They should share the same lower-level building blocks wherever possible.

### 2. MCP Tool Layer

The MCP server in `harness/server.py` is the source of truth for external tools. It auto-discovers tool modules from `harness/tools/` and registers functions listed in each module's `TOOLS` list.

That means the harness follows an MCP-first contract:

- the loop asks the MCP client for available tools
- those tools are converted into model-visible function schemas
- the model is called with those tool definitions
- returned tool calls are sent back through the MCP client

This is an important architectural choice. The loop is not supposed to know about individual filesystem tools, shell tools, or other application-specific capabilities. It only knows how to consume a tool source and dispatch calls.

### 3. Shared Loop Engine

The core loop now lives in `harness/utils/loop/`.

Its responsibilities are intentionally narrow:

- stream model output
- collect tool calls
- mutate conversation state
- dispatch tools
- emit streaming events
- return once a final assistant message is produced

Key modules:

- `runner.py`
  The core loop driver.
- `tool_registry.py`
  Fetches MCP tools and combines them with orchestration-defined pseudo-tools.
- `tool_dispatch.py`
  Executes tool calls through either the MCP client or registered special handlers.
- `state.py`
  Holds the shared message-state helpers.
- `response.py`
  Normalizes streamed tool-call payloads.
- `events.py`
  Keeps transport-specific event emission out of the loop body.

The loop is meant to stay generic. It should not know about SQLite, Discord, or hardcoded tool names like `delegate_agent`.

### 4. Orchestration Layer

The harness-specific behavior lives in `harness/utils/orchestration/`.

This is where the system decides things like:

- which system prompt to use
- which model role to run
- how many loop rounds are allowed
- which pseudo-tools should be exposed in addition to MCP tools
- which special handlers should intercept certain tool calls

Current orchestration pieces:

- `prompts.py`
  Defines the orchestrator, delegated-agent, and chat prompts.
- `policy.py`
  Builds the default policy object for a conversation run.
- `delegation.py`
  Implements `delegate_agent` as an orchestration-owned pseudo-tool rather than a hardcoded branch in the loop.

This is the main line between generic mechanics and harness-specific behavior. If a change is about how this harness should behave, it probably belongs here rather than in the loop engine itself.

### 5. Inference Layer

The inference seam lives in `harness/utils/inference/`.

Its job is to hide provider-specific details from the rest of the application. Right now the active backend is Ollama, but the rest of the harness should not care about that beyond choosing a model role such as `orchestrator`, `delegate`, or `chat`.

Current structure:

- `base.py`
  Shared stream-chunk shape and inference protocol.
- `ollama.py`
  Ollama-specific implementation.
- `registry.py`
  Maps model roles to configured models and returns the active inference client.

The important rule is simple: direct provider construction belongs here, not in interface code, not in `llm.py`, and not in orchestration modules.

### 6. Conversation State And Persistence

Conversation state and durable storage are now split on purpose.

#### In-memory state

`harness/utils/context/` owns the compatibility `ConversationManager` surface and the `ConversationState` namespace. This is the layer that callers use when they need to load, save, or carry around a conversation in process.

#### Durable storage

`harness/utils/persistence/` owns the storage boundary.

- `base.py`
  Defines the repository contract.
- `sqlite_conversations.py`
  Implements the SQLite-backed repository.

This repository stores more than plain message text. It also keeps message metadata, including tool-call payloads, so conversations can round-trip more faithfully than before.

The intended separation is:

- interfaces load and save through `context/`
- `context/` coordinates with `persistence/`
- the loop only mutates in-memory state

That keeps SQLite concerns away from the core loop.

### 7. Interface Layers

The two user-facing interfaces currently have different responsibilities but share more core plumbing than before.

#### Web

`harness/web/server.py` handles:

- WebSocket communication
- conversation commands such as new/load/delete
- event forwarding from the loop to the browser
- persistence through `ConversationManager`

The web interface is the closest to the full MCP-capable harness path because it connects to the shared `llm.loop(...)` compatibility entrypoint.

#### Discord

`harness/discord/bot.py` handles:

- Discord message intake
- per-channel session state
- optional summarize flow
- streamed response rendering

Discord still has some interface-specific behavior, especially around rendering and message windowing, but it now uses the shared inference and config layers instead of creating its own direct Ollama client.

## Current Request Flow In More Detail

### Web request flow

1. Browser sends a message over WebSocket.
2. `harness/web/server.py` appends the user message to the current conversation.
3. It calls `harness.utils.llm.loop(...)`.
4. `llm.py` builds the shared state and default orchestration policy, then forwards into `loop/runner.py`.
5. `runner.py` asks `tool_registry.py` for the final model-visible tool list.
6. The inference client streams the model response.
7. If tool calls are returned, `tool_dispatch.py` routes them through MCP or orchestration handlers.
8. Results are appended to state and the loop continues.
9. When a final assistant response is produced, the interface receives streaming events and saves the updated conversation.

### Delegation flow

1. The orchestrator policy adds `delegate_agent` as a pseudo-tool.
2. If the model calls it, `tool_dispatch.py` routes it to the special handler from `orchestration/delegation.py`.
3. A restricted sub-agent client is created with only the allowed tool names.
4. The same shared loop runner is reused for the delegated run.
5. The delegated result is returned as a tool result back to the parent conversation.

This is important because delegation is now policy-driven rather than hardcoded into the loop engine.

## Notes On Current State

The repo still has signs of earlier experiments and planned future work:

- `harness/utils/providers/` is now a historical placeholder.
- there are compiled artifacts and old database files in the tree from previous runs.
- the root architecture is cleaner than before, but the tool inventory and some interface behavior are still early-stage.

That is normal for the current phase. The main win is that the architecture has clearer boundaries now, so future work can extend the harness without dumping new responsibilities into `llm.py`.

## Makefile

The `Makefile` is meant to give you fast local entrypoints for testing the stack.

- `make mcp`
  Starts the FastMCP tool server.
- `make web`
  Starts the web UI server.
- `make discord`
  Starts the Discord bot.
- `make stack`
  Starts the MCP server and web UI together.
- `make dev`
  Starts MCP, web, and Discord together for full-stack testing.
- `make check`
  Runs a quick Python compile pass over the repo to catch syntax-level issues.
- `make help`
  Prints the available targets.

The practical workflow is:

- use `make stack` when you want the main browser-based harness path
- use `make dev` when you want everything running at once
- use `make check` after refactors when you want a fast sanity check
