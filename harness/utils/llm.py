from harness.utils.context.conversation_state import ConversationState
from harness.utils.inference import get_default_registry
from harness.utils.loop.runner import run_conversation
from harness.utils.orchestration.policy import build_default_policy


async def loop(client, messages, on_event=None):
    state = ConversationState.from_messages(messages)
    registry = get_default_registry()
    policy = build_default_policy()
    result = await run_conversation(
        client,
        state,
        policy,
        registry.get_client(),
        on_event=on_event,
    )
    messages[:] = state.to_messages()
    return result
