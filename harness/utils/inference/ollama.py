from .base import StreamChunk


class OllamaInferenceClient:
    def __init__(self):
        import ollama

        self._client = ollama.AsyncClient()

    async def stream_chat(
        self,
        *,
        model: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        think: bool | str | None = None,
    ):
        kwargs = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if tools is not None:
            kwargs["tools"] = tools
        if think is not None:
            kwargs["think"] = think

        async for chunk in await self._client.chat(**kwargs):
            message = chunk.get("message", {})
            yield StreamChunk(
                content=message.get("content", ""),
                thinking=message.get("thinking", ""),
                tool_calls=message.get("tool_calls") or [],
            )
