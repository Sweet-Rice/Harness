import ollama
from .logger import log_thinking


#determines extended thinking. decided each chat.
_thinking = False

_aclient = ollama.AsyncClient()


async def print_event(event_type, content):
    """Default callback — prints to terminal."""
    print(content)


async def get_tools(client):
    tools = await client.list_tools()
    ollama_tools = []
    for t in tools:
        ollama_tools.append({
            "type": "function",
            "function":{
                "name": t.name,
                "description": t.description,
                "parameters": t.inputSchema,
            }
        })
    return ollama_tools


MAX_TOOL_ROUNDS = 15


async def _stream(messages, ollama_tools, on_event):
    """Call LLM with tools. Streams tokens. Returns (content, tool_calls)."""
    await on_event("stream_start", "")
    full_content = ""
    full_thinking = ""
    tool_calls = None

    async for chunk in await _aclient.chat(
        model="qwen3-coder",
        messages=messages,
        tools=ollama_tools,
        think=_thinking,
        stream=True,
    ):
        if chunk.message.thinking:
            full_thinking += chunk.message.thinking
            await on_event("stream_thinking", chunk.message.thinking)
        if chunk.message.content:
            full_content += chunk.message.content
            await on_event("stream_token", chunk.message.content)
        if chunk.message.tool_calls:
            tool_calls = chunk.message.tool_calls

    await on_event("stream_end", "")

    if full_thinking:
        log_thinking(full_thinking)

    return full_content, tool_calls


async def loop(client, messages, on_event=None):
    if on_event is None:
        on_event = print_event

    ollama_tools = await get_tools(client)

    await on_event("status", "cooking")

    for _ in range(MAX_TOOL_ROUNDS):
        content, tool_calls = await _stream(messages, ollama_tools, on_event)

        if tool_calls:
            tool_names = ', '.join(tc.function.name for tc in tool_calls)
            await on_event("log", f"DEBUG -- tools: {tool_names}")

            assistant_msg = {"role": "assistant", "content": content}
            assistant_msg["tool_calls"] = [
                {"function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ]
            messages.append(assistant_msg)

            for tc in tool_calls:
                result = await client.call_tool(
                    tc.function.name,
                    tc.function.arguments,
                )
                await on_event("log", f"TOOL -- {tc.function.name} returned: {result.data}")
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


def set_thinking(value: bool):
    global _thinking
    _thinking = value
