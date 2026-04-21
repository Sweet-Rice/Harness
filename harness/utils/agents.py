from harness.utils.config import SETTINGS
from harness.utils.inference import get_default_registry
from harness.utils.orchestration.delegation import (
    build_delegate_handler,
    delegate_agent_tool,
)
from harness.utils.orchestration.prompts import get_delegate_system_prompt


SUB_AGENT_SYSTEM_PROMPT = get_delegate_system_prompt()
DELEGATE_AGENT_TOOL_DEF = delegate_agent_tool()


async def run_sub_agent(client, prompt, tool_names, on_event=None):
    handler = build_delegate_handler(get_default_registry(), SETTINGS)
    return await handler(
        client=client,
        args={"prompt": prompt, "tools": tool_names},
        on_event=on_event,
    )
