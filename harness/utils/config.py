import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _first_env(*names: str, default: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


def parse_think_setting(value: str) -> bool | str:
    normalized = value.strip().lower()
    if normalized in {"", "false", "0", "off", "no"}:
        return False
    if normalized in {"true", "1", "on", "yes"}:
        return True
    return value.strip()


@dataclass(frozen=True)
class HarnessConfig:
    provider: str = "ollama"
    orchestrator_model: str = "qwen3.5:latest"
    delegate_model: str = "qwen3.5:latest"
    chat_model: str = "gemma4:latest"
    max_loop_rounds: int = 15
    max_delegate_rounds: int = 10
    discord_max_context_messages: int = 20
    think: bool | str = False

    @classmethod
    def from_env(cls) -> "HarnessConfig":
        orchestrator_model = _first_env(
            "HARNESS_MODEL_ORCHESTRATOR",
            "HARNESS_MODEL",
            "HARNESS:MODEL",
            default="qwen3.5:latest",
        )
        delegate_model = _first_env(
            "HARNESS_MODEL_DELEGATE",
            "HARNESS_MODEL",
            "HARNESS:MODEL",
            default=orchestrator_model,
        )
        chat_model = _first_env(
            "HARNESS_MODEL_CHAT",
            "HARNESS_MODEL",
            default="gemma4:latest",
        )
        return cls(
            provider=os.environ.get("HARNESS_PROVIDER", "ollama"),
            orchestrator_model=orchestrator_model,
            delegate_model=delegate_model,
            chat_model=chat_model,
            max_loop_rounds=max(1, int(os.environ.get("HARNESS_MAX_LOOP_ROUNDS", "15"))),
            max_delegate_rounds=max(
                1, int(os.environ.get("HARNESS_MAX_DELEGATE_ROUNDS", "10"))
            ),
            discord_max_context_messages=max(
                2, int(os.environ.get("HARNESS_MAX_CONTEXT_MESSAGES", "20"))
            ),
            think=parse_think_setting(os.environ.get("HARNESS_THINK", "false")),
        )


SETTINGS = HarnessConfig.from_env()
