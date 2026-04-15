import asyncio
import json
import http
import http.server
import threading
from pathlib import Path

import websockets

from fastmcp import Client
from harness.utils.supervisor import run
from harness.utils.prompts import SYSTEM_PROMPT
from harness.utils.context import ConversationManager


STATIC_DIR = Path(__file__).parent / "static"
HTTP_PORT = 8765
WS_PORT = 8766


async def handle_ws(websocket):
    async def send(msg_type, content):
        await websocket.send(json.dumps({"type": msg_type, "content": content}))

    client = Client("http://localhost:8000/mcp")
    ctx = ConversationManager()
    messages = [SYSTEM_PROMPT.copy()]
    ctx.new("Default")

    async def send_conversations():
        convos = ctx.list()
        await websocket.send(json.dumps({
            "type": "conversations",
            "content": convos,
            "current": ctx.current,
        }))

    try:
        async with client:
            await send_conversations()

            async for raw in websocket:
                data = json.loads(raw)

                # Handle commands
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
                            # Replay user/assistant messages to the UI
                            for m in messages:
                                if m.get("role") == "user":
                                    await send("user", m["content"])
                                elif m.get("role") == "assistant":
                                    await send("message", m["content"])
                        await send_conversations()

                    elif cmd == "delete":
                        cid = data.get("id", "")
                        ctx.delete(cid)
                        if cid == ctx.current:
                            ctx.new("Default")
                            messages = [SYSTEM_PROMPT.copy()]
                        await send("system", f"Deleted: {cid}")
                        await send_conversations()

                    elif cmd == "rename":
                        ctx.rename(data.get("id", ""), data.get("name", ""))
                        await send_conversations()

                    continue

                # Handle chat messages
                user_text = data.get("content", "")

                # Support slash commands from chat input
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

                messages.append({"role": "user", "content": user_text})

                async def on_event(event_type, content):
                    await websocket.send(json.dumps({"type": event_type, "content": content}))

                try:
                    await run(client, messages, on_event)
                    ctx.save(ctx.current, messages)
                except Exception as exc:
                    await send("system", f"Backend error: {exc}")
                    await send("status", "idle")
    except Exception as exc:
        try:
            await send("system", f"Backend startup error: {exc}")
            await send("status", "idle")
        except Exception:
            pass


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
