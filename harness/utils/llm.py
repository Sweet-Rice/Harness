import json
from dataclasses import dataclass

from harness.config import load_config
from harness.utils.inference import InferenceClient
from harness.utils.logger import log_thinking


_config = load_config()
_inference = InferenceClient(_config)


@dataclass
class DelegationRequest:
    """Returned by loop() when the orchestrator calls run_agent."""
    agent_name: str
    task: str


def get_inference() -> InferenceClient:
    """Get the shared InferenceClient instance."""
    return _inference


async def print_event(event_type, content):
    """Default callback — prints to terminal."""
    if event_type in ("stream_token", "stream_thinking"):
        print(content, end="", flush=True)
    elif event_type == "stream_end":
        print()
    else:
        print(content)


async def get_tools(client):
    """Convert MCP tool list to provider-agnostic tool dicts."""
    tools = await client.list_tools()
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.inputSchema,
            },
        }
        for t in tools
    ]


def _build_run_agent_tool() -> dict:
    """Build the run_agent virtual tool definition from the agent registry."""
    from harness.utils.agents import list_agents

    agents = list_agents()
    agent_list = "\n".join(
        f'  - "{a.name}": {a.description}' for a in agents
    )

    return {
        "type": "function",
        "function": {
            "name": "run_agent",
            "description": (
                "Delegate a task to a specialized agent. "
                "Available agents:\n" + agent_list
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the agent to run",
                    },
                    "task": {
                        "type": "string",
                        "description": "The task description for the agent",
                    },
                },
                "required": ["agent_name", "task"],
            },
        },
    }


async def _stream(messages, tools, on_event, *, role="orchestrator"):
    """Stream from inference, emit events. Returns (content, tool_calls)."""
    await on_event("stream_start", "")
    full_content = ""
    full_thinking = ""
    tool_calls = []

    async for chunk in _inference.stream(
        role,
        messages,
        tools=tools,
    ):
        if chunk.thinking:
            full_thinking += chunk.thinking
            await on_event("stream_thinking", chunk.thinking)
        if chunk.content:
            full_content += chunk.content
            await on_event("stream_token", chunk.content)
        if chunk.tool_calls:
            tool_calls = chunk.tool_calls

    await on_event("stream_end", "")

    if full_thinking:
        log_thinking(full_thinking)

    return full_content, tool_calls


async def loop(client, messages, on_event=None, *, role=None, allowed_tools=None):
    """Main tool-calling loop.

    Returns None on normal completion, or a DelegationRequest when the
    orchestrator calls run_agent (supervisor handles the context switch).

    Args:
        allowed_tools: If None (orchestrator), injects run_agent virtual tool.
                       If a list, filters MCP tools to that set.
    """
    if on_event is None:
        on_event = print_event

    use_role = role or _config.default_role
    tools = await get_tools(client)

    if allowed_tools is None:
        # Orchestrator: inject run_agent
        tools.append(_build_run_agent_tool())
    else:
        # Sub-agent: filter to allowed tools only
        tools = [t for t in tools if t["function"]["name"] in allowed_tools]

    await on_event("status", "cooking")

    for _ in range(_config.max_tool_rounds):
        content, tool_calls = await _stream(
            messages, tools, on_event, role=use_role
        )

        if tool_calls:
            tool_names = ", ".join(tc.name for tc in tool_calls)
            await on_event("log", f"DEBUG -- tools: {tool_names}")

            assistant_msg = {"role": "assistant", "content": content}
            assistant_msg["tool_calls"] = [
                {"function": {"name": tc.name, "arguments": tc.arguments}}
                for tc in tool_calls
            ]
            messages.append(assistant_msg)

            for tc in tool_calls:
                # Intercept run_agent — return delegation request
                if tc.name == "run_agent":
                    await on_event("log", f"DELEGATE -- {tc.arguments}")
                    await on_event("delegation_start", json.dumps({
                        "agent_name": tc.arguments["agent_name"],
                        "task": tc.arguments["task"],
                    }))
                    return DelegationRequest(
                        agent_name=tc.arguments["agent_name"],
                        task=tc.arguments["task"],
                    )

                await on_event("tool_start", json.dumps({
                    "name": tc.name,
                    "arguments": tc.arguments,
                }))

                try:
                    result = await client.call_tool(tc.name, tc.arguments)
                    await on_event("log", f"TOOL -- {tc.name} returned: {result.data}")
                    await on_event("tool_result", json.dumps({
                        "name": tc.name,
                        "result": str(result.data)[:2000],
                        "is_error": False,
                    }))
                    messages.append({"role": "tool", "content": str(result)})
                except Exception as e:
                    error_msg = f"Error: tool '{tc.name}' failed — {e}"
                    await on_event("log", f"TOOL ERROR -- {error_msg}")
                    await on_event("tool_result", json.dumps({
                        "name": tc.name,
                        "result": error_msg,
                        "is_error": True,
                    }))
                    messages.append({"role": "tool", "content": error_msg})
            continue

        # No tool calls — model is done
        messages.append({"role": "assistant", "content": content})
        await on_event("message", content)
        await on_event("status", "idle")
        return None

    # Exhausted rounds
    await on_event("log", "WARN -- max tool rounds reached")
    await on_event("message", content)
    await on_event("status", "idle")
    return None
