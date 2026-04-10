# Layer 7: User Interface

## Purpose
All interfaces hit the same orchestrator. CLI first, voice second, web and mobile later.

## Status
PARTIAL

## What Exists

### CLI (`harness/harness.py`, 96 lines)
- Terminal-based conversation interface
- Commands: `/new`, `/list`, `/load`, `/delete`, `/rename`
- Calls `loop()` from `harness/utils/llm.py` for each user input
- Saves conversation state via `ConversationManager`
- Terminal-based approval prompt for write proposals

### Web UI
- **Server** (`harness/web/server.py`, 144 lines):
  - HTTP server on port 8765 (serves static files)
  - WebSocket server on port 8766 (real-time communication)
  - Handles conversation management commands over WebSocket
  - Streams events to frontend
  - Approval queue wiring for write proposals
- **Frontend** (`harness/web/static/index.html`, 365 lines):
  - Sidebar with conversation list + "New Chat" button
  - Main message area with scrolling
  - Input bar with Send button
  - WebSocket client with auto-reconnect
  - Markdown rendering via marked.js
  - Thinking display (collapsible)
  - "cooking" status indicator with animated dots
  - Git-style diff display for write proposals with Approve/Deny buttons

### MCP Server (`harness/server.py`)
- FastMCP HTTP server on port 8000
- Exposes all tools via MCP protocol

## What's Planned

### Voice Input (STT)
- Whisper-based speech-to-text for voice commands
  - Location: `harness/interface/voice.py` (new)
  - Depends on: Whisper model (local), audio capture library

### Voice Output (TTS)
- Text-to-speech for agent responses
  - Location: integrated into `harness/interface/voice.py`
  - Depends on: TTS engine selection (local)

### Mobile Interface
- Long-term goal — details TBD
  - Likely a web app optimized for mobile, reusing the WebSocket backend

## Architecture
```
┌─────────┐  ┌─────────┐  ┌──────────┐  ┌────────┐
│   CLI   │  │  Web UI  │  │  Voice   │  │ Mobile │
└────┬────┘  └────┬────┘  └────┬─────┘  └───┬────┘
     │            │            │             │
     ▼            ▼            ▼             ▼
┌─────────────────────────────────────────────────┐
│         Orchestrator (loop in llm.py)           │
└─────────────────────────────────────────────────┘
```

All interfaces call the same `loop()` function with different `on_event` callbacks.

## Key Decisions
- **CLI first**: Simplest to build and debug, always available
- **Web second**: Richer UI for streaming, diffs, conversations
- **Same orchestrator for all interfaces**: No interface-specific logic in the core

## Open Questions
- Voice: always-listening mode or push-to-talk?
- Voice: wake word ("Hey Jarvis") or manual activation?
- Mobile: native app or PWA (progressive web app)?
- Should the web UI support multi-user or is this single-user only?
