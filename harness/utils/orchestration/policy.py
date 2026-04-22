from dataclasses import dataclass, field

from harness.utils.config import SETTINGS
from harness.utils.inference import get_default_registry

from .delegation import build_delegate_handler, delegate_agent_tool
from .prompts import get_chat_system_prompt, get_orchestrator_system_prompt
from .skills import build_skill_handler, skill_trigger_tool


@dataclass
class OrchestrationPolicy:
    registry: object
    model_role: str
    system_prompt: dict
    max_rounds: int
    think: bool | str | None = None
    client_type: str = "web"
    allowed_mcp_tools: tuple[str, ...] | None = None
    special_tools: list[dict] = field(default_factory=list)
    special_handlers: dict = field(default_factory=dict)


def _discord_allowed_tool_names() -> tuple[str, ...]:
    return tuple(SETTINGS.discord_tool_allowlist)


def _filter_special_tools(
    tools: list[dict],
    handlers: dict,
    *,
    allowed_names: tuple[str, ...] | None,
):
    if allowed_names is None:
        return tools, handlers

    allowed = set(allowed_names)
    filtered_tools = [
        tool
        for tool in tools
        if tool.get("function", {}).get("name") in allowed
    ]
    filtered_handlers = {
        name: handler for name, handler in handlers.items() if name in allowed
    }
    return filtered_tools, filtered_handlers


def build_policy(
    mode: str = "orchestrated",
    *,
    client_type: str = "web",
):
    registry = get_default_registry()
    allowed_mcp_tools = None
    if client_type == "discord":
        allowed_mcp_tools = _discord_allowed_tool_names()

    if mode == "chat":
        return OrchestrationPolicy(
            registry=registry,
            model_role="chat",
            system_prompt=get_chat_system_prompt(),
            max_rounds=SETTINGS.max_loop_rounds,
            think=SETTINGS.think,
            client_type=client_type,
            allowed_mcp_tools=(),
        )

    delegate_tool = delegate_agent_tool()
    delegate_handler = build_delegate_handler(
        registry,
        SETTINGS,
        allowed_tool_names=allowed_mcp_tools,
    )
    skill_tool = skill_trigger_tool()
    skill_handler = build_skill_handler(registry)
    special_tools, special_handlers = _filter_special_tools(
        [delegate_tool, skill_tool],
        {
            "delegate_agent": delegate_handler,
            "trigger_skill": skill_handler,
        },
        allowed_names=allowed_mcp_tools,
    )
    return OrchestrationPolicy(
        registry=registry,
        model_role="orchestrator",
        system_prompt=get_orchestrator_system_prompt(),
        max_rounds=SETTINGS.max_loop_rounds,
        think=SETTINGS.think,
        client_type=client_type,
        allowed_mcp_tools=allowed_mcp_tools,
        special_tools=special_tools,
        special_handlers=special_handlers,
    )


def build_default_policy():
    return build_policy("orchestrated", client_type="web")
