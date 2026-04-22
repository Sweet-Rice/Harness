# Tools

This directory contains MCP tool implementations that the Harness MCP server registers at startup.

## What This Directory Owns

Each tool module defines plain Python callables and exports them through:

```python
TOOLS = [my_tool]
```

`harness/server.py` imports each module under `harness/tools/` and registers every callable listed in `TOOLS`.

That means this directory is the source of truth for:
- raw MCP tool implementations
- the callable signatures the MCP server exposes
- local safety checks that belong to the tool itself

It is not the source of truth for which client may use which tool. Tool exposure policy lives in orchestration/client policy, not here.

## How To Add A New Tool

1. Create a new module in `harness/tools/`.
2. Define one or more plain Python functions.
3. Keep the function signature simple and MCP-friendly.
4. Export the functions in `TOOLS = [...]`.

Example shape:

```python
def my_tool(arg: str) -> str:
    ...

TOOLS = [my_tool]
```

## Safety Expectations

Tools should be conservative by default.

Important rules:
- filesystem tools should require absolute paths
- dangerous tools should validate inputs locally instead of assuming the model used them correctly
- if a tool would mutate important state, prefer a proposal/approval shape over silent mutation
- tool errors should be returned cleanly enough that the loop can surface them back to the model

The current file tools are a good example of the intended baseline:
- reads require absolute paths
- binary files return an error instead of crashing the loop
- writes return a structured proposal instead of mutating immediately

## Tools And Client Policy

A tool being registered on the MCP server does not mean every client should see it.

Two separate layers exist:
- MCP registration: "this tool exists on the server"
- orchestration/client policy: "this model session is allowed to see this tool"

Right now:
- web orchestrated chat can expose the broader tool set
- Discord is default-deny and only sees allowlisted tools

That separation is intentional. Do not try to enforce per-client exposure by editing tool modules directly.

## Tools Versus Skills

Tools are low-level capabilities.
Skills are higher-level intent triggers.

A skill may:
- build a payload from conversation state
- choose a restricted prompting path
- optionally use tools in a controlled way later

A skill is not:
- "all tools exposed everywhere"
- a replacement for raw MCP tools
- a reason to bypass orchestration policy

If you are adding a new user-facing action, decide first whether it is:
- a raw capability that belongs in `harness/tools/`
- or an intent-layer action that belongs in shared orchestration skill handling

When in doubt, put user-facing trigger logic in the skill/orchestration layer and keep tools narrow.
