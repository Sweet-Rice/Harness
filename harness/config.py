from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


CONFIG_PATH = Path(__file__).parent.parent / "harness.toml"


@dataclass
class ProviderConfig:
    name: str
    base_url: str = ""


@dataclass
class ModelConfig:
    provider: str
    model: str
    think: bool = False
    options: dict = field(default_factory=dict)


@dataclass
class HarnessConfig:
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    models: dict[str, ModelConfig] = field(default_factory=dict)
    default_role: str = "orchestrator"
    db_path: str = ""
    thinking_log: str = ""
    max_tool_rounds: int = 15
    searxng_url: str = ""


def load_config(path: Path = CONFIG_PATH) -> HarnessConfig:
    """Load config from TOML file, falling back to defaults."""
    if not path.exists():
        return _defaults()

    with open(path, "rb") as f:
        raw = tomllib.load(f)

    config = HarnessConfig()

    # Providers
    for key, val in raw.get("providers", {}).items():
        config.providers[key] = ProviderConfig(
            name=val.get("name", key),
            base_url=val.get("base_url", ""),
        )

    # Models (role → model config)
    for key, val in raw.get("models", {}).items():
        config.models[key] = ModelConfig(
            provider=val["provider"],
            model=val["model"],
            think=val.get("think", False),
            options=val.get("options", {}),
        )

    config.default_role = raw.get("default_role", "orchestrator")
    config.db_path = raw.get("db_path", "")
    config.thinking_log = raw.get("thinking_log", "")
    config.max_tool_rounds = raw.get("max_tool_rounds", 15)

    services = raw.get("services", {})
    config.searxng_url = services.get("searxng_url", "")

    return config


def _defaults() -> HarnessConfig:
    """Defaults matching current behavior — Ollama with gemma4."""
    return HarnessConfig(
        providers={"ollama": ProviderConfig(name="ollama")},
        models={
            "orchestrator": ModelConfig(provider="ollama", model="gemma4:latest"),
            "coder": ModelConfig(provider="ollama", model="qwen3-coder"),
            "reviewer": ModelConfig(provider="ollama", model="gemma4:latest"),
        },
    )
