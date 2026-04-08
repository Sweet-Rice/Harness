import asyncio
import json
import http
import http.server
import threading
from pathlib import Path

import websockets

from fastmcp import Client
from harness.utils.llm import loop, summarize_title
from harness.utils.prompts import SYSTEM_PROMPT
from harness.utils.context import ConversationManager


STATIC_DIR = Path(__file__).parent / "static"
HTTP_PORT = 8765
WS_PORT = 8766


async def handle_ws(websocket):
    client = Client("http://localhost:8000/mcp")
    ctx = ConversationManager()
    convos = ctx.list()
    if convos:
        messages = ctx.load(convos[0]["id"]) or [SYSTEM_PROMPT.copy()]
    else:
        ctx.new("Default")
        messages = [SYSTEM_PROMPT.copy()]
    approval_queue = asyncio.Queue()
    chat_queue = asyncio.Queue()
    current_task = None  # tracks the running loop() task for stop

    async def send(msg_type, content):
        await websocket.send(json.dumps({"type": msg_type, "content": content}))

    async def send_conversations():
        convos = ctx.list()
        await websocket.send(json.dumps({
            "type": "conversations",
            "content": convos,
            "current": ctx.current,
        }))

    async def on_event(event_type, content):
        await websocket.send(json.dumps({"type": event_type, "content": content}))

    async def ws_reader():
        """Read all WebSocket messages, dispatch to appropriate queues."""
        nonlocal messages
        async for raw in websocket:
            data = json.loads(raw)

            # Approval responses go straight to the approval queue
            if data.get("command") == "approve":
                await approval_queue.put(data.get("approved", False))
                continue

            # Stop cancels the current loop() task
            if data.get("command") == "stop":
                if current_task and not current_task.done():
                    current_task.cancel()
                continue

            # Other commands handled inline
            if "command" in data:
                cmd = data["command"]

                if cmd == "new":
                    if ctx.current:
                        ctx.save(ctx.current, messages)
                    cid = ctx.new(name=data.get("name"))
                    messages = [SYSTEM_PROMPT.copy()]
                    await send("system", f"New conversation: {cid}")
                    await send_conversations()

                elif cmd == "list":
                    await send_conversations()

                elif cmd == "load":
                    cid = data.get("id", "")
                    if ctx.current:
                        ctx.save(ctx.current, messages)
                    loaded = ctx.load(cid)
                    if loaded is None:
                        await send("system", f"Conversation {cid} not found.")
                    else:
                        messages = loaded
                        await send("system", f"Loaded conversation: {cid}")
                        for m in messages:
                            if m.get("role") == "user":
                                await send("user", m["content"])
                            elif m.get("role") == "assistant":
                                await send("message", m["content"])
                    await send_conversations()

                elif cmd == "delete":
                    cid = data.get("id", "")
                    was_current = (cid == ctx.current)
                    ctx.delete(cid)
                    if was_current:
                        remaining = ctx.list()
                        if remaining:
                            messages = ctx.load(remaining[0]["id"]) or [SYSTEM_PROMPT.copy()]
                        else:
                            ctx.new("Default")
                            messages = [SYSTEM_PROMPT.copy()]
                    await send("system", f"Deleted: {cid}")
                    await send_conversations()

                elif cmd == "rename":
                    ctx.rename(data.get("id", ""), data.get("name", ""))
                    await send_conversations()

                continue

            # Chat messages go to the chat queue
            await chat_queue.put(data)

    async def chat_processor():
        """Process chat messages sequentially."""
        nonlocal messages, current_task
        while True:
            data = await chat_queue.get()
            user_text = data.get("content", "")

            # Slash commands from chat input
            if user_text.startswith("/"):
                parts = user_text.split(maxsplit=1)
                cmd = parts[0]
                arg = parts[1] if len(parts) > 1 else ""

                if cmd == "/new":
                    if ctx.current:
                        ctx.save(ctx.current, messages)
                    cid = ctx.new(name=arg or None)
                    messages = [SYSTEM_PROMPT.copy()]
                    await send("system", f"New conversation: {cid}")
                    await send_conversations()
                    continue
                elif cmd == "/list":
                    await send_conversations()
                    continue

            is_first_message = sum(1 for m in messages if m.get("role") == "user") == 0
            messages.append({"role": "user", "content": user_text})
            loop_task = asyncio.create_task(
                loop(client, messages, on_event=on_event, approval_queue=approval_queue)
            )
            current_task = loop_task
            try:
                await loop_task
            except asyncio.CancelledError:
                await on_event("system", "Stopped.")
            finally:
                current_task = None
            ctx.save(ctx.current, messages)

            if is_first_message:
                async def _auto_title(cid, text):
                    try:
                        title = await summarize_title(text)
                        if title:
                            ctx.rename(cid, title)
                            await send_conversations()
                    except Exception:
                        pass
                asyncio.create_task(_auto_title(ctx.current, user_text))

    async with client:
        await send_conversations()

        # Run reader and chat processor concurrently
        reader_task = asyncio.create_task(ws_reader())
        processor_task = asyncio.create_task(chat_processor())

        try:
            # Wait for the reader to finish (WebSocket close)
            await reader_task
        finally:
            processor_task.cancel()


def serve_http():
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

        def log_message(self, format, *args):
            pass

    server = http.server.HTTPServer(("0.0.0.0", HTTP_PORT), Handler)
    server.serve_forever()


async def main():
    threading.Thread(target=serve_http, daemon=True).start()
    print(f"Web UI: http://localhost:{HTTP_PORT}")
    print(f"WebSocket: ws://localhost:{WS_PORT}")

    async with websockets.serve(handle_ws, "0.0.0.0", WS_PORT):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
