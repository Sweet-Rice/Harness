import asyncio
import json
import http
import http.server
import threading
from pathlib import Path

import websockets

from fastmcp import Client
from harness.utils.config import SETTINGS
from harness.utils.llm import loop
from harness.utils.context import ConversationManager
from harness.utils.orchestration.skills import build_skill_payload, execute_skill


STATIC_DIR = Path(__file__).parent / "static"


async def handle_ws(websocket):
    client = Client(SETTINGS.mcp_url)
    ctx = ConversationManager()
    messages = []
    web_source = "web"
    web_client_id = "default"

    async def send(msg_type, content):
        await websocket.send(json.dumps({"type": msg_type, "content": content}))

    async def send_conversations():
        convos = ctx.list(source=web_source, client_id=web_client_id, include_global=True)
        await websocket.send(json.dumps({
            "type": "conversations",
            "content": convos,
            "current": ctx.current,
        }))

    def reset_messages():
        return []

    def ensure_current_conversation():
        nonlocal messages
        if ctx.current is None:
            ctx.new(
                "Default",
                thread_type="global_thread",
                mode="orchestrated",
                source=web_source,
                client_id=web_client_id,
            )
            messages = reset_messages()

    def load_most_recent_conversation():
        nonlocal messages
        convos = ctx.list(source=web_source, client_id=web_client_id, include_global=True)
        if not convos:
            messages = reset_messages()
            return
        loaded = ctx.load_thread(convos[0]["id"])
        messages = loaded.messages if loaded is not None else reset_messages()

    async with client:
        load_most_recent_conversation()
        await send_conversations()

        async for raw in websocket:
            data = json.loads(raw)

            # Handle commands
            if "command" in data:
                cmd = data["command"]

                if cmd == "new":
                    if ctx.current:
                        ctx.save(ctx.current, messages)
                    thread = ctx.create_thread(
                        data.get("name"),
                        thread_type="global_thread",
                        mode="orchestrated",
                        source=web_source,
                        client_id=web_client_id,
                    )
                    messages = reset_messages()
                    await send("system", f"New conversation: {thread.id}")
                    await send_conversations()

                elif cmd == "list":
                    await send_conversations()

                elif cmd == "load":
                    cid = data.get("id", "")
                    if ctx.current:
                        ctx.save(ctx.current, messages)
                    loaded = ctx.load_thread(cid)
                    if loaded is None:
                        await send("system", f"Conversation {cid} not found.")
                    else:
                        messages = loaded.messages
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
                    was_current = cid == ctx.current
                    ctx.delete(cid)
                    if was_current:
                        load_most_recent_conversation()
                    await send("system", f"Deleted: {cid}")
                    await send_conversations()

                elif cmd == "rename":
                    ctx.rename(data.get("id", ""), data.get("name", ""))
                    await send_conversations()

                elif cmd == "skill":
                    skill_name = data.get("skill_name", "").strip()
                    extra_payload = data.get("payload", "").strip()
                    if not skill_name:
                        await send("system", "Usage: /skill <skill_name> [extra instructions]")
                        continue
                    transcript = build_skill_payload(skill_name, messages)
                    if extra_payload:
                        transcript = f"{transcript}\n\n[extra_instructions] {extra_payload}".strip()
                    result = await execute_skill(
                        skill_name,
                        transcript,
                        client_type="web",
                        registry=None,
                    )
                    await send("message", result or "Skill returned no output.")

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
                    thread = ctx.create_thread(
                        arg or None,
                        thread_type="global_thread",
                        mode="orchestrated",
                        source=web_source,
                        client_id=web_client_id,
                    )
                    messages = reset_messages()
                    await send("system", f"New conversation: {thread.id}")
                    await send_conversations()
                    continue
                elif cmd == "/list":
                    await send_conversations()
                    continue
                elif cmd == "/skill":
                    skill_parts = arg.split(maxsplit=1)
                    skill_name = skill_parts[0].strip() if skill_parts else ""
                    extra_payload = skill_parts[1].strip() if len(skill_parts) > 1 else ""
                    if not skill_name:
                        await send("system", "Usage: /skill <skill_name> [extra instructions]")
                        continue
                    transcript = build_skill_payload(skill_name, messages)
                    if extra_payload:
                        transcript = f"{transcript}\n\n[extra_instructions] {extra_payload}".strip()
                    result = await execute_skill(
                        skill_name,
                        transcript,
                        client_type="web",
                        registry=None,
                    )
                    await send("message", result or "Skill returned no output.")
                    continue

            ensure_current_conversation()
            messages.append({"role": "user", "content": user_text})

            async def on_event(event_type, content):
                await websocket.send(json.dumps({"type": event_type, "content": content}))

            await loop(client, messages, on_event=on_event, mode="orchestrated", client_type="web")
            if ctx.current:
                ctx.save(ctx.current, messages)


def serve_http():
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

        def do_GET(self):
            if self.path == "/runtime-config.json":
                ws_url = SETTINGS.web_ws_url or (
                    f"ws://{self.headers.get('Host', '').split(':')[0] or 'localhost'}:{SETTINGS.web_ws_port}"
                )
                body = json.dumps({"ws_url": ws_url}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            return super().do_GET()

        def log_message(self, format, *args):
            pass

    server = http.server.HTTPServer((SETTINGS.web_host, SETTINGS.web_http_port), Handler)
    server.serve_forever()


async def main():
    threading.Thread(target=serve_http, daemon=True).start()
    print(f"Web UI: http://localhost:{SETTINGS.web_http_port}")
    print(f"WebSocket: ws://localhost:{SETTINGS.web_ws_port}")

    async with websockets.serve(handle_ws, SETTINGS.web_ws_host, SETTINGS.web_ws_port):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
