from dataclasses import dataclass, field

from harness.utils.config import SETTINGS
from harness.utils.inference import get_default_registry

from .delegation import build_delegate_handler, delegate_agent_tool
from .prompts import get_orchestrator_system_prompt


@dataclass
class OrchestrationPolicy:
    registry: object
    model_role: str
    system_prompt: dict
    max_rounds: int
    think: bool | str | None = None
    special_tools: list[dict] = field(default_factory=list)
    special_handlers: dict = field(default_factory=dict)


def build_default_policy():
    registry = get_default_registry()
    delegate_tool = delegate_agent_tool()
    delegate_handler = build_delegate_handler(registry, SETTINGS)
    return OrchestrationPolicy(
        registry=registry,
        model_role="orchestrator",
        system_prompt=get_orchestrator_system_prompt(),
        max_rounds=SETTINGS.max_loop_rounds,
        special_tools=[delegate_tool],
        special_handlers={"delegate_agent": delegate_handler},
    )
