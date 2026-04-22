from harness.utils.loop.events import EventEmitter

from .tool_dispatch import dispatch_tool_call
from .tool_registry import list_tools


async def run_conversation(client, state, policy, inference, on_event=None):
    emitter = EventEmitter(on_event)
    state.ensure_system_message(policy.system_prompt)
    tools = await list_tools(client, policy_tools=policy.special_tools)
    model = policy.registry.model_for(policy.model_role)

    for _ in range(policy.max_rounds):
        full_content = ""
        tool_calls = []

        await emitter.stream_start()
        async for chunk in inference.stream_chat(
            model=model,
            messages=state.to_model_messages(),
            tools=tools or None,
            think=policy.think,
        ):
            if chunk.thinking:
                await emitter.stream_thinking(chunk.thinking)
            if chunk.content:
                full_content += chunk.content
                await emitter.stream_token(chunk.content)
            if chunk.tool_calls:
                tool_calls = chunk.tool_calls
        await emitter.stream_end()

        if tool_calls:
            state.append_assistant_with_tool_calls(full_content, tool_calls)
            for tool_call in tool_calls:
                name, _, result_text = await dispatch_tool_call(
                    client,
                    tool_call,
                    handlers=policy.special_handlers,
                    on_event=on_event,
                )
                state.append_tool_result(name, result_text)
        else:
            state.append_message("assistant", full_content)
            await emitter.message(full_content)
            return full_content

    final_message = "Error: maximum tool rounds reached before the model produced a final response."
    state.append_message("assistant", final_message)
    await emitter.message(final_message)
    return final_message
