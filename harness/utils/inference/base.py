from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class StreamChunk:
    content: str = ""
    thinking: str = ""
    tool_calls: list[Any] = field(default_factory=list)


class InferenceClient(Protocol):
    async def stream_chat(
        self,
        *,
        model: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        think: bool | str | None = None,
    ):
        ...
