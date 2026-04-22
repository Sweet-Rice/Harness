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
from harness.utils.orchestration.plan_state import OrchestratedRunService
from harness.utils.orchestration.skills import (
    available_skill_entries,
    build_skill_payload,
    execute_skill,
)


STATIC_DIR = Path(__file__).parent / "static"
WEB_COMMANDS = [
    {
        "name": "/new",
        "description": "Start a fresh orchestrated web conversation.",
        "scaffold": "/new ",
        "type": "command",
    },
    {
        "name": "/list",
        "description": "Refresh the conversation list.",
        "scaffold": "/list",
        "type": "command",
    },
]


def summarize_web_request_label(text: str, max_length: int = 52) -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return "New Chat"
    words = cleaned.split()
    summary = " ".join(words[:8])
    if len(summary) > max_length:
        summary = summary[: max_length - 1].rstrip() + "…"
    elif len(words) > 8 or len(cleaned) > len(summary):
        summary = summary.rstrip(".,;:!?")
        if len(summary) < len(cleaned):
            summary += "…"
    return summary


def should_autorename_web_thread(thread, messages) -> bool:
    if thread is None or thread.source != "web":
        return False
    if len(messages) != 1:
        return False
    name = (thread.name or "").strip()
    return name == "Default" or name.startswith("Chat ")


async def handle_ws(websocket):
    client = Client(SETTINGS.mcp_url)
    ctx = ConversationManager()
    orchestration = OrchestratedRunService()
    messages = []
    current_thread = None
    active_run = None
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

    async def emit_trace(event_type, content):
        await send(event_type, content)

    async def send_plan_trace():
        if active_run is None:
            return
        try:
            plan = orchestration.load_plan(active_run)
        except Exception:
            return
        await send("trace.plan_update", orchestration.plan_trace_payload(plan))

    def reset_messages():
        return []

    def ensure_current_conversation():
        nonlocal messages, current_thread
        if ctx.current is None:
            thread = ctx.create_thread(
                "Default",
                thread_type="global_thread",
                mode="orchestrated",
                source=web_source,
                client_id=web_client_id,
            )
            current_thread = thread
            messages = reset_messages()

    def load_most_recent_conversation():
        nonlocal messages, current_thread, active_run
        convos = ctx.list(source=web_source, client_id=web_client_id, include_global=True)
        if not convos:
            current_thread = None
            active_run = None
            messages = reset_messages()
            return
        loaded = ctx.load_thread(convos[0]["id"])
        if loaded is None:
            current_thread = None
            active_run = None
            messages = reset_messages()
            return
        current_thread = loaded.thread
        messages = loaded.messages
        active_run = None
        if loaded.thread.mode == "orchestrated" and loaded.thread.thread_type == "global_thread":
            active_run = orchestration.load_or_create_session(loaded.thread, messages)
            return

    async with client:
        load_most_recent_conversation()
        await send_conversations()
        await send_plan_trace()

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
                    current_thread = thread
                    active_run = None
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
                        current_thread = loaded.thread
                        messages = loaded.messages
                        active_run = None
                        if loaded.thread.mode == "orchestrated" and loaded.thread.thread_type == "global_thread":
                            active_run = orchestration.load_or_create_session(loaded.thread, messages)
                        await send("system", f"Loaded conversation: {cid}")
                        # Replay user/assistant messages to the UI
                        for m in messages:
                            if m.get("role") == "user":
                                await send("user", m["content"])
                            elif m.get("role") == "assistant":
                                await send("message", m["content"])
                        await send_plan_trace()
                    await send_conversations()

                elif cmd == "delete":
                    cid = data.get("id", "")
                    was_current = cid == ctx.current
                    deleted = ctx.load_thread(cid)
                    if deleted is not None and deleted.thread.mode == "orchestrated":
                        orchestration.delete_for_thread(cid, mode=deleted.thread.mode)
                    ctx.delete(cid)
                    if was_current:
                        load_most_recent_conversation()
                        await send_plan_trace()
                    await send("system", f"Deleted: {cid}")
                    await send_conversations()

                elif cmd == "rename":
                    ctx.rename(data.get("id", ""), data.get("name", ""))
                    if current_thread is not None and current_thread.id == data.get("id", ""):
                        current_thread.name = data.get("name", "")
                    if active_run is not None and active_run.thread_id == data.get("id", ""):
                        active_run.thread_name = data.get("name", "")
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
                    current_thread = thread
                    active_run = None
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
            if current_thread is None and ctx.current:
                loaded = ctx.load_thread(ctx.current)
                if loaded is not None:
                    current_thread = loaded.thread
            if should_autorename_web_thread(current_thread, messages):
                new_name = summarize_web_request_label(user_text)
                ctx.rename(current_thread.id, new_name)
                current_thread.name = new_name
                if active_run is not None and active_run.thread_id == current_thread.id:
                    active_run.thread_name = new_name
                await send_conversations()
            runtime_messages = messages
            if (
                current_thread is not None
                and current_thread.mode == "orchestrated"
                and current_thread.thread_type == "global_thread"
            ):
                active_run = orchestration.load_or_create_session(current_thread, messages)
                await orchestration.sync_before_turn(active_run, messages, on_event=emit_trace)
                runtime_messages = orchestration.build_runtime_messages(active_run, messages)

            async def on_event(event_type, content):
                if event_type == "stream_thinking":
                    await send("trace.main_thinking", {"content": content})
                    return
                if event_type in {
                    "trace.subagent_thinking",
                    "trace.subagent_status",
                    "trace.plan_update",
                    "trace.tool_event",
                    "trace.log",
                }:
                    await send(event_type, content)
                    return
                if event_type == "log":
                    await send("trace.log", {"content": content})
                    return
                await send(event_type, content)

            await loop(
                client,
                runtime_messages,
                on_event=on_event,
                mode="orchestrated",
                client_type="web",
            )
            if active_run is not None and runtime_messages is not messages:
                messages[:] = [
                    dict(message)
                    for message in runtime_messages
                    if message.get("role") != "system"
                ]
                await orchestration.sync_after_turn(active_run, messages, on_event=emit_trace)
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
                body = json.dumps(
                    {
                        "ws_url": ws_url,
                        "skills": [
                            {
                                "name": entry["name"],
                                "description": entry["description"],
                                "scaffold": f"/skill {entry['name']} ",
                                "type": "skill",
                            }
                            for entry in available_skill_entries()
                        ],
                        "commands": WEB_COMMANDS,
                    }
                ).encode("utf-8")
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
