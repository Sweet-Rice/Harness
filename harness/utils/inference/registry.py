from dataclasses import dataclass

from harness.utils.config import HarnessConfig, SETTINGS

from .base import InferenceClient
from .ollama import OllamaInferenceClient


@dataclass
class InferenceRegistry:
    settings: HarnessConfig
    _client: InferenceClient | None = None

    def get_client(self) -> InferenceClient:
        if self.settings.provider != "ollama":
            raise ValueError(f"Unsupported provider: {self.settings.provider}")
        if self._client is None:
            self._client = OllamaInferenceClient()
        return self._client

    def model_for(self, role: str) -> str:
        if role == "orchestrator":
            return self.settings.orchestrator_model
        if role == "delegate":
            return self.settings.delegate_model
        if role == "chat":
            return self.settings.chat_model
        raise ValueError(f"Unknown model role: {role}")


_default_registry: InferenceRegistry | None = None


def get_default_registry() -> InferenceRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = InferenceRegistry(SETTINGS)
    return _default_registry
