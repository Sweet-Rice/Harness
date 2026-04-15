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

### Execution Tools
| Tool | File | Description |
|------|------|-------------|
| `read_file` | `harness/tools/files.py` | Read file contents (absolute path required) |
| `write_file` | `harness/tools/files.py` | Write content to a file (no approval flow yet) |
| `web_search` | `harness/tools/search.py` | Search the web via SearXNG, return top results |
| `fetch_url` | `harness/tools/search.py` | Fetch a URL and return readable text content |

### Plan Management Tools
| Tool | File | Description |
|------|------|-------------|
| `create_plan` | `harness/tools/plans.py` | Create a new plan in PlanStore |
| `get_plan` | `harness/tools/plans.py` | Read a plan by ID |
| `update_plan` | `harness/tools/plans.py` | Update plan text (appends diff) |
| `set_plan_status` | `harness/tools/plans.py` | Set plan status (active/completed/failed/paused) |
| `list_plans` | `harness/tools/plans.py` | List plans, optionally filtered |
| `get_plan_diffs` | `harness/tools/plans.py` | Get change history for a plan |

### Virtual Tools (injected by harness, not MCP)
| Tool | Location | Description |
|------|----------|-------------|
| `run_agent` | `harness/utils/llm.py` | Delegate task to a premade agent (planner, coder). Orchestrator only. |

### Deleted in Refactor (no longer exist)
- `plan()`, `plan_review()` — old orchestration tools that wrapped `ollama.chat()` directly
- `output()`, `output_review()` — inner tool loop, caused tool hallucination
- `review_code` — LLM-powered code review
- `enable_thinking`, `disable_thinking` — runtime thinking toggle
- `ping`, `shell` — utility/stub tools

## What's Planned
- **Shell execution** (`harness/tools/shell.py`): Run shell commands with output capture. Requires user confirmation for dangerous commands.
- **Write approval flow**: Restore proposal-based write_file — diff display, user approve/deny. Currently write_file writes directly.
- **Thinking toggle**: Runtime tool to toggle the `think` config field per model.
- **Calendar integration**: Read/write calendar events (Google Calendar or CalDAV).
- **Email**: Read/send email (Gmail or IMAP/SMTP). Requires user confirmation for sends.
- **Home automation**: Control smart devices. Requires user confirmation.
- **Music control**: Play/pause/search music (Spotify, etc.).
- **Code execution sandbox**: Run code in an isolated environment.

## Architecture
```
harness/tools/
  ├─ __init__.py
  ├─ files.py          (read_file, write_file)
  ├─ search.py         (web_search, fetch_url)
  ├─ plans.py          (create_plan, get_plan, update_plan, set_plan_status, list_plans, get_plan_diffs)
  ├─ shell.py          (planned)
  ├─ calendar.py       (planned)
  ├─ email.py          (planned)
  ├─ home.py           (planned)
  ├─ music.py          (planned)
  └─ sandbox.py        (planned)

Virtual (injected into LLM tool list, not MCP):
  └─ run_agent         (built dynamically from agent registry in llm.py)
```

Each module exports `TOOLS = [func1, func2, ...]`. The server auto-discovers them.

## Key Decisions
- **MCP as transport**: Model Context Protocol for tool registration and invocation
- **Auto-discovery**: `pkgutil.iter_modules` + `TOOLS` list export pattern — no central registry to maintain
- **No tools with embedded LLM calls**: Old pattern (tools wrapping `ollama.chat()`) was removed. Agent delegation handles LLM-powered sub-tasks instead.
- **Per-agent tool filtering**: Agents only see their allowed tools (via `allowed_tools` in `loop()`). Orchestrator gets `run_agent`; sub-agents don't.

## Open Questions
- Auth strategy for external services (calendar, email, music) — OAuth tokens stored where?
- Dangerous action confirmation: which tools require user approval beyond write_file? (shell, email, home automation)
