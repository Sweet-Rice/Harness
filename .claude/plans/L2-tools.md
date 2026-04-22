# Layer 2: Tool Use

## Purpose

The agent can take actions in the world. Each raw capability is registered declaratively via MCP or exposed as an orchestration-owned pseudo-tool. Adding a capability should not require editing the core loop.

## Status

PARTIAL

## What Exists

### Tool Infrastructure

- FastMCP server in `harness/server.py` with auto-discovery via `pkgutil`
- Each tool module exports `TOOLS = [...]`
- Shared tool registration in `harness/utils/loop/tool_registry.py`
- Shared tool dispatch in `harness/utils/loop/tool_dispatch.py`

### Current MCP Tools

| Tool | File | Description |
|------|------|-------------|
| `read_file` | `harness/tools/files.py` | Read UTF-8 file contents from absolute paths |
| `write_file` | `harness/tools/files.py` | Return a structured non-mutating write proposal |

### Current Orchestration-Owned Pseudo-Tools

| Tool | Owner | Description |
|------|-------|-------------|
| `delegate_agent` | `utils/orchestration/delegation.py` | Restricted sub-agent execution |
| `trigger_skill` | `utils/orchestration/skills.py` | Explicit higher-level skill trigger |

### Current Policy Boundary

- MCP registration and client exposure are intentionally separate
- Web and Discord do not implicitly share the same visible tool set
- Discord is default-deny and only sees allowlisted tools/pseudo-tools

## What's Planned

- **Shell execution**
  Run shell commands with output capture and explicit confirmation for dangerous actions
- **Web search**
  Search and summarize external results
- **Calendar integration**
  Read/write calendar events with proper auth
- **Email**
  Read/send email, with confirmation for sends
- **Home automation**
  Control local devices with explicit confirmation
- **Music control**
  Playback/search integration
- **Code execution sandbox**
  Execute code in an isolated environment

These can land either as raw MCP tools or as higher-level skill/orchestration entrypoints, but raw capability should still live behind the tool boundary.

## Architecture

```
harness/tools/           → raw MCP tools
harness/server.py        → MCP registration
utils/loop/              → tool schema + dispatch
utils/orchestration/     → pseudo-tools + policy
clients (web/discord)    → filtered exposure only
```

## Key Decisions

- MCP remains the transport and registration model
- Auto-discovery via `TOOLS = [...]` remains the default registration pattern
- Dangerous actions should prefer proposal/approval contracts over silent mutation
- Client visibility and raw tool existence are different concerns

## Open Questions

- Which future tools require confirmation?
- How fine-grained should per-agent/per-client tool policy become?
- Where should credentials for external-service tools live?
