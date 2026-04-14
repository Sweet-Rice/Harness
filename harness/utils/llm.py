from harness.config import load_config
from harness.utils.inference import InferenceClient
from harness.utils.logger import log_thinking


_config = load_config()
_inference = InferenceClient(_config)


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


async def loop(client, messages, on_event=None, *, role=None):
    if on_event is None:
        on_event = print_event

    use_role = role or _config.default_role
    tools = await get_tools(client)

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
                result = await client.call_tool(tc.name, tc.arguments)
                await on_event("log", f"TOOL -- {tc.name} returned: {result.data}")
                messages.append({"role": "tool", "content": str(result)})
            continue

        # No tool calls — model is done
        messages.append({"role": "assistant", "content": content})
        await on_event("message", content)
        await on_event("status", "idle")
        return

    # Exhausted rounds
    await on_event("log", "WARN -- max tool rounds reached")
    await on_event("message", content)
    await on_event("status", "idle")
