import ollama

from harness.utils.inference import (
    InferenceProvider,
    InferenceResult,
    StreamChunk,
    ToolCallInfo,
)


class OllamaProvider(InferenceProvider):

    def __init__(self, config):
        self._client = ollama.AsyncClient(
            host=config.base_url or None,
        )

    async def chat(self, messages, *, model, tools=None, think=False, options=None):
        response = await self._client.chat(
            model=model,
            messages=messages,
            tools=tools or [],
            think=think,
            options=options or {},
        )
        return InferenceResult(
            content=response.message.content or "",
            thinking=response.message.thinking or "",
            tool_calls=_extract_tool_calls(response.message.tool_calls),
        )

    async def stream(self, messages, *, model, tools=None, think=False, options=None):
        async for chunk in await self._client.chat(
            model=model,
            messages=messages,
            tools=tools or [],
            think=think,
            stream=True,
            options=options or {},
        ):
            yield StreamChunk(
                content=chunk.message.content or "",
                thinking=chunk.message.thinking or "",
                tool_calls=_extract_tool_calls(chunk.message.tool_calls),
            )


def _extract_tool_calls(raw_calls) -> list[ToolCallInfo]:
    if not raw_calls:
        return []
    return [
        ToolCallInfo(
            name=tc.function.name,
            arguments=tc.function.arguments,
        )
        for tc in raw_calls
    ]
