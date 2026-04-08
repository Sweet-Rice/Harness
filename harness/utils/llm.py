import asyncio
import json
import subprocess
from pathlib import Path

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


MAX_TOOL_ROUNDS = 40


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


def _parse_proposals(result_data):
    """Extract proposals from a tool result. Returns (text, proposals_list).

    Handles two formats:
    - Single proposal: {"type": "proposal", ...}
    - Multi-proposal from output(): {"text": "...", "proposals": [...]}
    """
    text = str(result_data)

    # Try parsing as JSON first
    try:
        # Look for the JSON content within MCP result wrapper
        start = text.find('{')
        if start == -1:
            return text, []

        # Find outermost JSON object
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    parsed = json.loads(text[start:i + 1])

                    # Multi-proposal format from output()
                    if "proposals" in parsed and isinstance(parsed["proposals"], list):
                        return parsed.get("text", ""), parsed["proposals"]

                    # Single proposal from write_file
                    if parsed.get("type") == "proposal":
                        return "", [parsed]

                    break
    except (json.JSONDecodeError, ValueError):
        pass

    return text, []


async def _handle_proposal(proposal, on_event, approval_queue):
    """Send proposal to UI, await approval, execute if approved."""
    proposal_event = {
        "path": proposal["path"],
        "diff": proposal["diff"],
        "command": proposal["command"],
    }
    if proposal.get("shell"):
        proposal_event["shell"] = True
    await on_event("proposal", json.dumps(proposal_event))

    approved = await approval_queue.get()

    if approved:
        if proposal.get("shell"):
            cmd = proposal["command"]
            try:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=120,
                )
                output = result.stdout
                if result.stderr:
                    output += f"\nSTDERR:\n{result.stderr}"
                if result.returncode != 0:
                    output += f"\nExit code: {result.returncode}"
                return f"Command executed: {cmd}\n{output}".strip()
            except subprocess.TimeoutExpired:
                return f"Command timed out after 120s: {cmd}"
        else:
            path = Path(proposal["path"]).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(proposal["content"])
            return f"File written successfully to: {proposal['path']}"
    else:
        if proposal.get("shell"):
            return f"User denied command: {proposal['command']}"
        return f"User denied write to: {proposal['path']}"


async def loop(client, messages, on_event=None, approval_queue=None):
    if on_event is None:
        on_event = print_event

    ollama_tools = await get_tools(client)

    await on_event("status", "cooking")

    try:
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
                    try:
                        result = await client.call_tool(
                            tc.function.name,
                            tc.function.arguments,
                        )
                    except Exception as e:
                        error_msg = f"Error calling {tc.function.name}: {e}"
                        await on_event("log", f"TOOL -- {error_msg}")
                        messages.append({"role": "tool", "content": error_msg})
                        continue

                    # Check for write proposals needing approval
                    text, proposals = _parse_proposals(result.data)
                    if proposals and approval_queue:
                        results = []
                        if text:
                            results.append(text)
                        for proposal in proposals:
                            outcome = await _handle_proposal(proposal, on_event, approval_queue)
                            results.append(outcome)
                        tool_result = "\n".join(results)
                        await on_event("log", f"TOOL -- {tc.function.name}: {tool_result}")
                        messages.append({"role": "tool", "content": tool_result})
                    else:
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

    except asyncio.CancelledError:
        await on_event("stream_end", "")
        await on_event("log", "Stopped by user.")
        await on_event("status", "idle")
        raise


def set_thinking(value: bool):
    global _thinking
    _thinking = value


async def summarize_title(user_message: str) -> str:
    """Generate a short conversation title from the first user message."""
    response = await _aclient.chat(
        model="qwen3-coder",
        messages=[
            {"role": "system", "content": "Generate a short title (max 6 words) for a conversation that starts with this message. Reply with ONLY the title, no quotes or punctuation."},
            {"role": "user", "content": user_message},
        ],
        think=False,
    )
    title = response.message.content.strip().strip('"\'')
    return title[:50]
