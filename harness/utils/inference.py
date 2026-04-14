from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional





"""
This is basically plumbing for the entire inference flow. Allows for modularity
"""

@dataclass
class ToolCallInfo:
    """Provider-agnostic representation of a tool call."""
    name: str
    arguments: dict


@dataclass
class StreamChunk:
    """Provider-agnostic chunk emitted during streaming."""
    content: str = ""
    thinking: str = ""
    tool_calls: list[ToolCallInfo] = field(default_factory=list)
    done: bool = False


@dataclass
class InferenceResult:
    """Provider-agnostic result of a non-streaming chat call."""
    content: str
    thinking: str = ""
    tool_calls: list[ToolCallInfo] = field(default_factory=list)


class InferenceProvider(ABC):
    """Abstract base class for inference providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        *,
        model: str,
        tools: Optional[list[dict]] = None,
        think: bool = False,
        options: Optional[dict] = None,
    ) -> InferenceResult:
        """Single-shot (non-streaming) chat completion."""
        ...

    @abstractmethod
    def stream(
        self,
        messages: list[dict],
        *,
        model: str,
        tools: Optional[list[dict]] = None,
        think: bool = False,
        options: Optional[dict] = None,
    ) -> AsyncIterator[StreamChunk]:
        """Streaming chat completion. Yields StreamChunk objects."""
        ...


class InferenceClient:
    """
    Entry point for all inference. Resolves roles to providers.

    Usage:
        client = InferenceClient(config)
        result = await client.chat("orchestrator", messages)
        async for chunk in client.stream("orchestrator", messages, tools=tools):
            ...
    """

    def __init__(self, config):
        from harness.config import HarnessConfig
        self._config: HarnessConfig = config
        self._providers: dict[str, InferenceProvider] = {}
        self._init_providers()

    def _init_providers(self):
        """Instantiate one provider per unique provider config."""
        for name, pconfig in self._config.providers.items():
            if pconfig.name == "ollama":
                from harness.utils.providers.ollama import OllamaProvider
                self._providers[name] = OllamaProvider(pconfig)
            else:
                raise ValueError(f"Unknown provider: {pconfig.name}")

    def _resolve(self, role: str):
        """Resolve a role name to (provider, model_config)."""
        model_config = self._config.models.get(role)
        if not model_config:
            raise ValueError(
                f"Unknown role: {role}. Defined: {list(self._config.models.keys())}"
            )
        provider = self._providers.get(model_config.provider)
        if not provider:
            raise ValueError(f"Unknown provider: {model_config.provider}")
        return provider, model_config

    async def chat(
        self,
        role: str,
        messages: list[dict],
        *,
        tools: Optional[list[dict]] = None,
        think: Optional[bool] = None,
    ) -> InferenceResult:
        provider, mconfig = self._resolve(role)
        use_think = think if think is not None else mconfig.think
        return await provider.chat(
            messages,
            model=mconfig.model,
            tools=tools,
            think=use_think,
            options=mconfig.options or None,
        )

    async def stream(
        self,
        role: str,
        messages: list[dict],
        *,
        tools: Optional[list[dict]] = None,
        think: Optional[bool] = None,
    ) -> AsyncIterator[StreamChunk]:
        provider, mconfig = self._resolve(role)
        use_think = think if think is not None else mconfig.think
        async for chunk in provider.stream(
            messages,
            model=mconfig.model,
            tools=tools,
            think=use_think,
            options=mconfig.options or None,
        ):
            yield chunk
