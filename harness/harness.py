import asyncio
from fastmcp import Client

from harness.utils.llm import print_event
from harness.utils.supervisor import run
from harness.utils.prompts import SYSTEM_PROMPT
from harness.utils.context import ConversationManager


ctx = ConversationManager()
messages = [SYSTEM_PROMPT.copy()]


def handle_command(cmd):
    global messages

    parts = cmd.strip().split(maxsplit=1)
    command = parts[0]
    arg = parts[1] if len(parts) > 1 else ""

    if command == "/new":
        # Save current conversation before switching
        if ctx.current:
            ctx.save(ctx.current, messages)
        cid = ctx.new(name=arg or None)
        messages = [SYSTEM_PROMPT.copy()]
        print(f"New conversation: {cid}")
        return True

    elif command == "/list":
        convos = ctx.list()
        if not convos:
            print("No conversations.")
        for c in convos:
            marker = " *" if c["id"] == ctx.current else ""
            print(f"  {c['id']}  {c['name']}  ({c['message_count']} msgs){marker}")
        return True

    elif command == "/load":
        if not arg:
            print("Usage: /load <id>")
            return True
        if ctx.current:
            ctx.save(ctx.current, messages)
        loaded = ctx.load(arg)
        if loaded is None:
            print(f"Conversation {arg} not found.")
        else:
            messages = loaded
            print(f"Loaded conversation: {arg}")
        return True

    elif command == "/delete":
        if not arg:
            print("Usage: /delete <id>")
            return True
        ctx.delete(arg)
        if arg == ctx.current:
            messages = [SYSTEM_PROMPT.copy()]
        print(f"Deleted: {arg}")
        return True

    elif command == "/rename":
        sub = arg.split(maxsplit=1)
        if len(sub) < 2:
            print("Usage: /rename <id> <name>")
            return True
        ctx.rename(sub[0], sub[1])
        print(f"Renamed {sub[0]} to: {sub[1]}")
        return True

    return False


async def main():
    global messages

    # Auto-create first conversation
    ctx.new("Default")

    client = Client("http://localhost:8000/mcp")
    async with client:
        while True:
            user_input = input("\nTask: ")

            if user_input.startswith("/"):
                if handle_command(user_input):
                    continue

            messages.append({"role": "user", "content": user_input})
            await run(client, messages, print_event)
            ctx.save(ctx.current, messages)


if __name__ == "__main__":
    asyncio.run(main())
