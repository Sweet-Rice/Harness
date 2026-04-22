"""Discord bot interface for the Harness AI assistant."""

from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass, field

import discord
from discord import app_commands
from discord.ext import commands
from fastmcp import Client

from harness.utils.config import SETTINGS
from harness.utils.context import ConversationManager
from harness.utils.inference import get_default_registry
from harness.utils.llm import loop
from harness.utils.orchestration.skills import (
    available_skill_names,
    build_skill_payload,
    execute_skill,
)
from harness.discord.renderer import TextRenderer


TOKEN = SETTINGS.discord_token
MAX_CONTEXT_MESSAGES = SETTINGS.discord_max_context_messages


@dataclass
class Session:
    ctx: ConversationManager
    thread_id: str
    mode: str
    messages: list[dict] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


sessions: dict[int, Session] = {}


def get_session(channel_id: int) -> Session:
    """Get or create a session for a Discord channel."""
    if channel_id not in sessions:
        ctx = ConversationManager()
        thread = ctx.get_or_create_client_scratch(
            source="discord",
            client_id=str(channel_id),
            name=f"discord-{channel_id}",
            mode="orchestrated",
        )
        sessions[channel_id] = Session(
            ctx=ctx,
            thread_id=thread.thread.id,
            mode=thread.thread.mode,
            messages=thread.messages,
        )
    return sessions[channel_id]


def _strip_mention(content: str, bot_id: int) -> str:
    """Remove the bot @mention from message content."""
    return content.replace(f"<@{bot_id}>", "").strip()


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=SETTINGS.discord_command_prefix, intents=intents)


def _window_messages(messages: list[dict]) -> list[dict]:
    """Keep the system prompt plus only the most recent conversation turns."""
    if len(messages) <= MAX_CONTEXT_MESSAGES:
        return messages

    system_messages = [m for m in messages if m.get("role") == "system"]
    non_system_messages = [m for m in messages if m.get("role") != "system"]
    keep_count = max(1, MAX_CONTEXT_MESSAGES - len(system_messages))
    return [*system_messages, *non_system_messages[-keep_count:]]


def _persist_session(session: Session):
    session.messages = _window_messages(session.messages)
    session.thread_id = session.ctx.current or session.thread_id
    session.ctx.save(session.thread_id, session.messages)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Harness bot online as {bot.user}")


@bot.tree.command(name="skill", description="Run an explicit Harness skill in this channel.")
@app_commands.describe(
    skill_name="The skill to run",
    payload="Optional extra instructions for the skill",
)
async def skill_command(
    interaction: discord.Interaction,
    skill_name: str,
    payload: str = "",
):
    await interaction.response.defer(thinking=True)

    session = get_session(interaction.channel_id)
    transcript = build_skill_payload(skill_name, session.messages)
    if payload.strip():
        transcript = f"{transcript}\n\n[extra_instructions] {payload.strip()}".strip()

    result = await execute_skill(
        skill_name,
        transcript,
        client_type="discord",
        registry=get_default_registry(),
    )
    await interaction.followup.send(result or "Skill returned no output.")


@skill_command.autocomplete("skill_name")
async def autocomplete_skill_name(
    interaction: discord.Interaction,
    current: str,
):
    del interaction
    current_lower = current.lower()
    return [
        app_commands.Choice(name=name, value=name)
        for name in available_skill_names()
        if current_lower in name.lower()
    ][:25]


@bot.tree.command(
    name="thread_new",
    description="Start a new local Discord scratch thread for this channel.",
)
async def thread_new_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=False)
    ctx = ConversationManager()
    thread = ctx.create_thread(
        name=f"discord-{interaction.channel_id}",
        thread_type="client_scratch",
        mode="orchestrated",
        source="discord",
        client_id=str(interaction.channel_id),
    )
    sessions[interaction.channel_id] = Session(
        ctx=ctx,
        thread_id=thread.id,
        mode=thread.mode,
        messages=[],
    )
    await interaction.followup.send(f"Started a new Discord scratch thread: `{thread.id}`")


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

    session = get_session(message.channel.id)

    async with session.lock, message.channel.typing():
        renderer = TextRenderer(edit_interval=SETTINGS.discord_edit_interval)
        await renderer.start(message.channel)

        try:
            session.messages.append({"role": "user", "content": user_text})

            async def on_event(event_type, content):
                if event_type == "stream_thinking":
                    await renderer.thinking(content)
                elif event_type == "stream_token":
                    await renderer.token(content)

            async with Client(SETTINGS.mcp_url) as client:
                await loop(
                    client,
                    session.messages,
                    on_event=on_event,
                    mode=session.mode,
                    client_type="discord",
                )
            _persist_session(session)
            await renderer.finish()

        except Exception as exc:
            await renderer.finish()
            await message.channel.send(f"Error: {exc}")
            # Remove the failed user message to keep history clean
            if session.messages and session.messages[-1].get("role") == "user":
                session.messages.pop()
        finally:
            print(
                f"[DEBUG] Total Discord request time: "
                f"{time.perf_counter() - started_at:.2f}s"
            )


def main():
    if not TOKEN:
        print("Error: set HARNESS_DISCORD_TOKEN environment variable", file=sys.stderr)
        sys.exit(1)
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
