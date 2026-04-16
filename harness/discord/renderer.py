"""Response rendering for Discord.

Renderer protocol + concrete implementations.
Swap renderers to change how bot responses look without touching the message handler.
"""

from __future__ import annotations

import asyncio
from typing import Protocol

import discord


MAX_MSG_LEN = 2000
MAX_EMBED_DESC_LEN = 4096


def split_message(text: str) -> list[str]:
    """Split text into chunks that fit Discord's 2000-char limit.

    Tries to break at newlines, then spaces, then hard-cuts.
    """
    if len(text) <= MAX_MSG_LEN:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= MAX_MSG_LEN:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, MAX_MSG_LEN)
        if split_at < MAX_MSG_LEN // 2:
            split_at = text.rfind(" ", 0, MAX_MSG_LEN)
        if split_at < MAX_MSG_LEN // 2:
            split_at = MAX_MSG_LEN
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks


class Renderer(Protocol):
    """Interface for Discord response rendering."""

    async def start(self, channel: discord.abc.Messageable) -> None: ...
    async def thinking(self, text: str) -> None: ...
    async def token(self, text: str) -> None: ...
    async def finish(self) -> str: ...


class TextRenderer:
    """Plain-text renderer that streams by editing a Discord message.

    Sends an initial message once content arrives, then edits it every
    ``edit_interval`` seconds with accumulated tokens.  On finish, does a
    final edit and sends overflow messages for content >2000 chars.
    """

    def __init__(self, *, edit_interval: float = 2.0):
        self.edit_interval = edit_interval
        self._channel: discord.abc.Messageable | None = None
        self._thinking = ""
        self._content = ""
        self._dirty = False
        self._msg: discord.Message | None = None
        self._done = False
        self._task: asyncio.Task | None = None

    async def start(self, channel: discord.abc.Messageable) -> None:
        self._channel = channel
        self._thinking = ""
        self._content = ""
        self._dirty = False
        self._msg = None
        self._done = False
        self._task = asyncio.create_task(self._edit_loop())

    async def thinking(self, text: str) -> None:
        self._thinking += text
        self._dirty = True

    async def token(self, text: str) -> None:
        self._content += text
        self._dirty = True

    async def finish(self) -> str:
        """Finalize the response.  Returns the full content string."""
        self._done = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._flush(final=True)
        return self._content

    # -- internals --

    async def _edit_loop(self) -> None:
        try:
            while not self._done:
                await asyncio.sleep(self.edit_interval)
                if self._dirty:
                    await self._flush()
        except asyncio.CancelledError:
            pass

    async def _flush(self, *, final: bool = False) -> None:
        if self._channel is None:
            return

        first, embed = self._render_message()
        if not first and embed is None:
            return

        chunks = split_message(self._content) if self._content else [""]
        first = chunks[0]

        if self._msg is None:
            self._msg = await self._channel.send(content=first or None, embed=embed)
        else:
            should_edit = first != self._msg.content
            if embed is not None:
                current_embed = self._msg.embeds[0] if self._msg.embeds else None
                current_desc = current_embed.description if current_embed else None
                next_desc = embed.description
                should_edit = should_edit or current_desc != next_desc
            elif self._msg.embeds:
                should_edit = True

            if should_edit:
                await self._msg.edit(content=first or None, embed=embed)

        # Send overflow chunks only on final flush to avoid partial overflow
        if final and len(chunks) > 1:
            for chunk in chunks[1:]:
                await self._channel.send(chunk)

        self._dirty = False

    def _render_message(self) -> tuple[str, discord.Embed | None]:
        embed = None
        if self._thinking:
            thinking = self._thinking
            if len(thinking) > MAX_EMBED_DESC_LEN:
                thinking = "..." + thinking[-(MAX_EMBED_DESC_LEN - 3):]
            embed = discord.Embed(title="Thinking", description=thinking)
        return self._content, embed
