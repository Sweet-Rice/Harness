from dataclasses import replace

from harness.utils.context.conversation_state import ConversationState
from harness.utils.loop.runner import run_conversation

from .prompts import get_delegate_system_prompt


def delegate_agent_tool() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "delegate_agent",
            "description": (
                "Delegate a task to a sub-agent. The sub-agent runs its own inference loop "
                "with access to only the specified tools. Returns the sub-agent's final response. "
                "Use this when a task requires focused work with specific tools."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The task description for the sub-agent. Be specific about what you want done.",
                    },
                    "tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tool names the sub-agent can use (e.g. ['read_file', 'write_file']).",
                    },
                },
                "required": ["prompt", "tools"],
            },
        },
    }


class RestrictedToolClient:
    def __init__(self, client, allowed_tool_names):
        self._client = client
        self._allowed_tool_names = set(allowed_tool_names)

    async def list_tools(self):
        tools = await self._client.list_tools()
        return [tool for tool in tools if tool.name in self._allowed_tool_names]

    async def call_tool(self, name, args):
        if name not in self._allowed_tool_names:
            raise ValueError(f"Tool '{name}' is not available to this agent.")
        return await self._client.call_tool(name, args)


def build_delegate_handler(registry, settings):
    inference = registry.get_client()

    async def handle_delegate(client, args, on_event=None):
        prompt = args["prompt"]
        tool_names = args["tools"]
        state = ConversationState.from_messages(
            [
                get_delegate_system_prompt(),
                {"role": "user", "content": prompt},
            ]
        )
        restricted_client = RestrictedToolClient(client, tool_names)
        policy = replace(
            build_delegate_policy(registry, settings),
            special_tools=[],
            special_handlers={},
        )

        async def subagent_event(event_type, content):
            if not on_event:
                return
            if event_type == "message":
                await on_event("log", "[sub-agent] completed task")
            elif event_type == "stream_start":
                await on_event("log", "[sub-agent] thinking...")
            elif event_type == "stream_end":
                return
            else:
                return

        result = await run_conversation(
            restricted_client,
            state,
            policy,
            inference,
            on_event=subagent_event,
        )
        return result or "[sub-agent reached maximum iterations without completing]"

    return handle_delegate


def build_delegate_policy(registry, settings):
    from .policy import OrchestrationPolicy

    return OrchestrationPolicy(
        registry=registry,
        model_role="delegate",
        system_prompt=get_delegate_system_prompt(),
        max_rounds=settings.max_delegate_rounds,
    )
