# Layer 7: User Interface

## Purpose

All interfaces should hit the same orchestrator stack. Interface code should be transport and presentation glue, not alternate assistant logic.

## Status

PARTIAL

## What Exists

### Web

- `harness/web/server.py`
  HTTP + WebSocket server for the browser UI
- `harness/web/static/index.html`
  Streaming chat frontend with conversation management and explicit slash-command skill triggering

Web uses the shared loop and, for orchestrated global threads, now mirrors canonical plan-state workspaces.

### Discord

- `harness/discord/bot.py`
  Shared-loop Discord client with real application slash commands
- `harness/discord/renderer.py`
  Streaming-friendly response renderer

Discord uses:
- shared inference/config/loop layers
- client-scratch threads by default
- default-deny tool exposure
- explicit slash-command skill triggering

### MCP Server

- `harness/server.py`
  FastMCP server that exposes raw MCP tools

## What's Planned

### Voice Input (STT)

- Whisper-style local speech-to-text

### Voice Output (TTS)

- Local text-to-speech for assistant responses

### Mobile Interface

- Likely a web-first or PWA-style client that reuses the shared backend

## Architecture

```
Web      Discord      Voice      Mobile
 │          │           │          │
 └──────────┴───────────┴──────────┘
                │
                ▼
      Shared loop + orchestration stack
```

## Key Decisions

- Interface-specific rendering belongs in interface code
- Tool policy, orchestration, persistence, and plan-state logic belong in shared layers
- Discord should stay stricter than web about tool exposure

## Open Questions

- Voice: always listening or push-to-talk?
- Voice: wake word or manual activation?
- Mobile: native app or PWA?
- How much multi-device synchronization should be exposed in the UI?
