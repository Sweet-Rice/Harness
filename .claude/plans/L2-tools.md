# Layer 2: Tool Use

## Purpose
The agent can take actions in the world. Each tool is a self-contained function registered declaratively via MCP. Adding a new capability means writing one function, not changing the core.

## Status
PARTIAL

## What Exists

### Tool Infrastructure
- FastMCP server in `harness/server.py` with auto-discovery via `pkgutil`
- Each tool module exports a `TOOLS` list
- Tools registered at startup, served on `http://0.0.0.0:8000`

### Orchestration Tools (each wraps its own `ollama.chat()` call)
| Tool | File | Description |
|------|------|-------------|
| `plan` | `harness/tools/plan.py` | Generate numbered step-by-step plan |
| `plan_review` | `harness/tools/plan.py` | Review plan against intent → PASS/FAIL |
| `output` | `harness/tools/output.py` | Execute plan, produce deliverable (inner tool loop) |
| `output_review` | `harness/tools/output.py` | Review output against plan + intent → PASS/FAIL |

### Execution Tools
| Tool | File | Description |
|------|------|-------------|
| `read_file` | `harness/tools/files.py` | Read file contents (absolute path required) |
| `write_file` | `harness/tools/files.py` | Propose file write — returns diff, requires user approval |

### Utility Tools
| Tool | File | Description |
|------|------|-------------|
| `review_code` | `harness/tools/review.py` | LLM-based pragmatic code review |
| `enable_thinking` | `harness/tools/thinking.py` | Enable extended thinking mode |
| `disable_thinking` | `harness/tools/thinking.py` | Disable extended thinking mode |
| `ping` | `harness/tools/ping.py` | Connection test |

### Stubs
| Tool | File | Description |
|------|------|-------------|
| `shell` | `harness/tools/shell.py` | Empty — 1 line stub |

## What's Planned
- **Shell execution** (`harness/tools/shell.py`): Run shell commands with output capture. Requires user confirmation for dangerous commands. Depends on: L3 (validation of command safety).
- **Web search**: Search the internet, return summarized results. Depends on: L1 (inference for summarization).
- **Calendar integration**: Read/write calendar events (Google Calendar or CalDAV). Depends on: auth infrastructure.
- **Email**: Read/send email (Gmail or IMAP/SMTP). Requires user confirmation for sends. Depends on: auth infrastructure.
- **Home automation**: Control smart devices. Requires user confirmation. Depends on: device API integration.
- **Music control**: Play/pause/search music. Depends on: service API (Spotify, etc.).
- **Code execution sandbox**: Run code in an isolated environment and return results. Depends on: sandboxing strategy.

## Architecture
```
harness/tools/
  ├─ __init__.py
  ├─ files.py          (read_file, write_file)
  ├─ plan.py           (plan, plan_review)
  ├─ output.py         (output, output_review)
  ├─ review.py         (review_code)
  ├─ thinking.py       (enable_thinking, disable_thinking)
  ├─ ping.py           (ping)
  ├─ shell.py          (stub → shell execution)
  ├─ search.py         (planned: web search)
  ├─ calendar.py       (planned: calendar)
  ├─ email.py          (planned: email)
  ├─ home.py           (planned: home automation)
  ├─ music.py          (planned: music)
  └─ sandbox.py        (planned: code execution)
```

Each module exports `TOOLS = [func1, func2, ...]`. The server auto-discovers them.

## Key Decisions
- **MCP as transport**: Model Context Protocol for tool registration and invocation
- **Auto-discovery**: `pkgutil.iter_modules` + `TOOLS` list export pattern — no central registry to maintain
- **Tools wrap their own LLM calls**: Orchestration tools (plan, output, review) each call `ollama.chat()` directly rather than delegating back to the orchestrator
- **Write approval required**: `write_file` returns a proposal, not a direct write

## Open Questions
- Which tools require user confirmation? Current list: write_file, shell (dangerous commands), email (sends), home automation. What else?
- Should tools have a permission/capability model (allowlist per agent)?
- Auth strategy for external services (calendar, email, music) — OAuth tokens stored where?
