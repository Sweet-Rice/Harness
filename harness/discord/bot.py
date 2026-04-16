"""Discord bot interface for the Harness AI assistant.

Calls Ollama directly for chat, persists conversations per channel via
ConversationManager, and streams responses through a pluggable Renderer.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass, field

import discord
import ollama
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

from harness.utils.context import ConversationManager
from harness.discord.renderer import TextRenderer


TOKEN = os.environ.get("HARNESS_DISCORD_TOKEN", "")
MODEL = os.environ.get("HARNESS_MODEL", "gemma4:latest")
MAX_CONTEXT_MESSAGES = max(2, int(os.environ.get("HARNESS_MAX_CONTEXT_MESSAGES", "20")))


def _parse_think_setting(value: str) -> bool | str:
    normalized = value.strip().lower()
    if normalized in {"", "false", "0", "off", "no"}:
        return False
    if normalized in {"true", "1", "on", "yes"}:
        return True
    return value.strip()


THINK = _parse_think_setting(os.environ.get("HARNESS_THINK", "false"))

SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "You are T.ai, a helpful personal AI assistant. "
        "You are running on the user's local machine via Ollama. "
        "Be concise and direct."
    ),
}


@dataclass
class Session:
    ctx: ConversationManager
    messages: list[dict] = field(default_factory=lambda: [SYSTEM_MESSAGE.copy()])
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


sessions: dict[int, Session] = {}


def get_session(channel_id: int) -> Session:
    """Get or create a session for a Discord channel."""
    if channel_id not in sessions:
        ctx = ConversationManager()
        ctx.new(f"discord-{channel_id}")
        sessions[channel_id] = Session(ctx=ctx)
    return sessions[channel_id]


def _strip_mention(content: str, bot_id: int) -> str:
    """Remove the bot @mention from message content."""
    return content.replace(f"<@{bot_id}>", "").strip()


DEFAULT_SUMMARY_COUNT = 50
MAX_SUMMARY_COUNT = 500

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


async def _fetch_history(channel: discord.abc.Messageable, count: int) -> str:
    """Fetch recent messages from a channel and format them for the LLM."""
    msgs: list[str] = []
    async for msg in channel.history(limit=count, oldest_first=False):
        if msg.author.bot:
            continue
        timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M")
        msgs.append(f"[{timestamp}] {msg.author.display_name}: {msg.content}")
    msgs.reverse()
    return "\n".join(msgs)


def _parse_summarize(text: str) -> int | None:
    """If text is a summarize request, return the message count.  Else None."""
    parts = text.strip().split()
    if not parts or parts[0].lower() != "summarize":
        return None
    if len(parts) >= 2 and parts[1].isdigit():
        return min(int(parts[1]), MAX_SUMMARY_COUNT)
    return DEFAULT_SUMMARY_COUNT


_ollama = ollama.AsyncClient()


def _window_messages(messages: list[dict]) -> list[dict]:
    """Keep the system prompt plus only the most recent conversation turns."""
    if len(messages) <= MAX_CONTEXT_MESSAGES:
        return messages

    system_messages = [m for m in messages if m.get("role") == "system"]
    non_system_messages = [m for m in messages if m.get("role") != "system"]
    keep_count = max(1, MAX_CONTEXT_MESSAGES - len(system_messages))
    return [*system_messages, *non_system_messages[-keep_count:]]


async def _stream_chat(messages: list[dict], renderer: TextRenderer) -> str:
    """Send messages to Ollama with streaming and return the full response."""
    start = time.perf_counter()
    ollama_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in _window_messages(messages)
    ]
    async for chunk in await _ollama.chat(
        model=MODEL,
        messages=ollama_messages,
        stream=True,
        think=THINK,
    ):
        message = chunk.get("message", {})
        thinking = message.get("thinking", "")
        token = message.get("content", "")
        if thinking:
            await renderer.thinking(thinking)
        if token:
            await renderer.token(token)
    elapsed = time.perf_counter() - start
    print(
        f"[DEBUG] Ollama stream finished in {elapsed:.2f}s "
        f"with {len(ollama_messages)} messages"
    )
    return await renderer.finish()


@bot.event
async def on_ready():
    print(f"Harness bot online as {bot.user}  (model: {MODEL})")


@bot.event
async def on_message(message: discord.Message):
    print(f"[DEBUG] msg from {message.author}: guild={message.guild}, content={message.content!r}")
    started_at = time.perf_counter()

    if message.author == bot.user or message.author.bot:
        return

    # In guilds, only respond to @mentions.  In DMs, always respond.
    if message.guild and not bot.user.mentioned_in(message):
        return

    user_text = _strip_mention(message.content, bot.user.id)
    if not user_text:
        return

    summary_count = _parse_summarize(user_text)
    session = get_session(message.channel.id)

    async with session.lock, message.channel.typing():
        renderer = TextRenderer()
        await renderer.start(message.channel)

        try:
            if summary_count is not None:
                # Summarize: fetch history and ask the LLM to summarize it
                history = await _fetch_history(message.channel, summary_count)
                prompt = (
                    f"Summarize the following Discord conversation "
                    f"({summary_count} most recent messages). "
                    f"Highlight key topics, decisions, and action items.\n\n"
                    f"{history}"
                )
                summary_messages = [
                    SYSTEM_MESSAGE.copy(),
                    {"role": "user", "content": prompt},
                ]
                full_content = await _stream_chat(summary_messages, renderer)
                # Don't persist summarize requests into the ongoing conversation
            else:
                # Normal chat
                session.messages.append({"role": "user", "content": user_text})
                full_content = await _stream_chat(session.messages, renderer)
                session.messages.append({"role": "assistant", "content": full_content})
                session.messages = _window_messages(session.messages)
                session.ctx.save(session.ctx.current, session.messages)

        except Exception as exc:
            await renderer.finish()
            await message.channel.send(f"Error: {exc}")
            # Remove the failed user message to keep history clean
            if (
                summary_count is None
                and session.messages
                and session.messages[-1].get("role") == "user"
            ):
                session.messages.pop()
        finally:
            print(
                f"[DEBUG] Total Discord request time: "
                f"{time.perf_counter() - started_at:.2f}s"
            )

    await bot.process_commands(message)


def main():
    if not TOKEN:
        print("Error: set HARNESS_DISCORD_TOKEN environment variable", file=sys.stderr)
        sys.exit(1)
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
