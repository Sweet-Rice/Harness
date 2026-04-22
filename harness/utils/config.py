import os
from dataclasses import dataclass
from pathlib import Path

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


def parse_csv_setting(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


@dataclass(frozen=True)
class HarnessConfig:
    # Model/provider configuration.
    provider: str = "ollama"
    orchestrator_model: str = "qwen3.5:latest"
    delegate_model: str = "qwen3.5:latest"
    chat_model: str = "gemma4:latest"

    # MCP deployment settings.
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000
    mcp_url: str = "http://localhost:8000/mcp"

    # Web interface network settings.
    web_host: str = "0.0.0.0"
    web_http_port: int = 8765
    web_ws_host: str = "0.0.0.0"
    web_ws_port: int = 8766
    web_ws_url: str | None = None

    # Shared persistence.
    db_path: str = str(Path(__file__).resolve().parents[1] / "jarvis.db")
    plan_store_path: str = str(Path(__file__).resolve().parents[1] / "plan_store")

    # Loop/runtime behavior.
    max_loop_rounds: int = 15
    max_delegate_rounds: int = 10
    discord_max_context_messages: int = 20
    think: bool | str = False

    # Discord interface settings.
    discord_token: str = ""
    discord_command_prefix: str = "!"
    discord_edit_interval: float = 2.0
    discord_tool_allowlist: tuple[str, ...] = ()

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
        mcp_host = os.environ.get("HARNESS_MCP_HOST", "0.0.0.0")
        mcp_port = max(1, int(os.environ.get("HARNESS_MCP_PORT", "8000")))
        mcp_url = _first_env(
            "HARNESS_MCP_URL",
            default=f"http://localhost:{mcp_port}/mcp",
        )
        web_host = os.environ.get("HARNESS_WEB_HOST", "0.0.0.0")
        web_http_port = max(1, int(os.environ.get("HARNESS_WEB_HTTP_PORT", "8765")))
        web_ws_host = os.environ.get("HARNESS_WEB_WS_HOST", "0.0.0.0")
        web_ws_port = max(1, int(os.environ.get("HARNESS_WEB_WS_PORT", "8766")))
        return cls(
            provider=os.environ.get("HARNESS_PROVIDER", "ollama"),
            orchestrator_model=orchestrator_model,
            delegate_model=delegate_model,
            chat_model=chat_model,
            mcp_host=mcp_host,
            mcp_port=mcp_port,
            mcp_url=mcp_url,
            web_host=web_host,
            web_http_port=web_http_port,
            web_ws_host=web_ws_host,
            web_ws_port=web_ws_port,
            web_ws_url=os.environ.get("HARNESS_WEB_WS_URL"),
            db_path=os.environ.get(
                "HARNESS_DB_PATH",
                str(Path(__file__).resolve().parents[1] / "jarvis.db"),
            ),
            plan_store_path=os.environ.get(
                "HARNESS_PLAN_STORE_PATH",
                str(Path(__file__).resolve().parents[1] / "plan_store"),
            ),
            max_loop_rounds=max(1, int(os.environ.get("HARNESS_MAX_LOOP_ROUNDS", "15"))),
            max_delegate_rounds=max(
                1, int(os.environ.get("HARNESS_MAX_DELEGATE_ROUNDS", "10"))
            ),
            discord_max_context_messages=max(
                2, int(os.environ.get("HARNESS_MAX_CONTEXT_MESSAGES", "20"))
            ),
            think=parse_think_setting(os.environ.get("HARNESS_THINK", "false")),
            discord_token=os.environ.get("HARNESS_DISCORD_TOKEN", ""),
            discord_command_prefix=os.environ.get("HARNESS_DISCORD_COMMAND_PREFIX", "!"),
            discord_edit_interval=float(os.environ.get("HARNESS_DISCORD_EDIT_INTERVAL", "2.0")),
            discord_tool_allowlist=parse_csv_setting(
                os.environ.get("HARNESS_DISCORD_TOOL_ALLOWLIST", "")
            ),
        )


SETTINGS = HarnessConfig.from_env()
