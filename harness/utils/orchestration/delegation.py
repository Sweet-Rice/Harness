from dataclasses import replace
import json

from harness.utils.context.conversation_state import ConversationState
from harness.utils.loop.runner import run_conversation

from .plan_model import DelegatedStepRequest, DelegatedStepResult
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
                        "description": "Compatibility field for the delegated task description. Prefer structured step fields for new callers.",
                    },
                    "step_id": {
                        "type": "string",
                        "description": "Optional explicit plan step id for one-step delegation.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional explicit step title for one-step delegation.",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Optional explicit step summary for one-step delegation.",
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional execution context pulled from canonical plan state.",
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


def _request_from_args(args: dict) -> DelegatedStepRequest:
    prompt = args.get("prompt", "").strip()
    step_id = (args.get("step_id") or "step-ad-hoc").strip()
    title = (args.get("title") or prompt or "Delegated plan step").strip()
    summary = (args.get("summary") or prompt or title).strip()
    context = (args.get("context") or "").strip()
    return DelegatedStepRequest(
        step_id=step_id,
        title=title,
        summary=summary,
        allowed_tools=[str(tool).strip() for tool in args.get("tools", []) if str(tool).strip()],
        execution_context=context,
    )


def _build_delegate_prompt(request: DelegatedStepRequest) -> str:
    return "\n".join(
        [
            "You are executing one explicit plan step.",
            f"Step ID: {request.step_id}",
            f"Title: {request.title}",
            f"Summary: {request.summary}",
            f"Allowed tools: {', '.join(request.allowed_tools) or 'none'}",
            "",
            "Execution context:",
            request.execution_context or "No extra context provided.",
            "",
            "Return a strict JSON object with these fields:",
            'step_id, status, summary, artifacts, follow_up_note, failure_reason',
            "Status must be one of: pending, in_progress, completed, blocked, failed.",
            "Do not wrap the JSON in markdown fences.",
        ]
    )


def _parse_delegate_result(request: DelegatedStepRequest, result_text: str) -> DelegatedStepResult:
    try:
        data = json.loads(result_text)
        return DelegatedStepResult(
            step_id=str(data.get("step_id") or request.step_id),
            status=str(data.get("status") or "completed"),
            summary=str(data.get("summary") or result_text.strip() or request.summary),
            artifacts=[str(item) for item in data.get("artifacts", [])],
            follow_up_note=str(data["follow_up_note"]) if data.get("follow_up_note") is not None else None,
            failure_reason=str(data["failure_reason"]) if data.get("failure_reason") is not None else None,
        )
    except Exception:
        return DelegatedStepResult(
            step_id=request.step_id,
            status="completed",
            summary=result_text.strip() or request.summary,
            artifacts=[],
            follow_up_note="Sub-agent returned an unstructured result; wrapped by the orchestrator compatibility layer.",
            failure_reason=None,
        )


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


def build_delegate_handler(registry, settings, *, allowed_tool_names=None):
    inference = registry.get_client()

    async def handle_delegate(client, args, on_event=None):
        request = _request_from_args(args)
        tool_names = list(request.allowed_tools)
        if allowed_tool_names is not None:
            allowed = set(allowed_tool_names)
            tool_names = [name for name in tool_names if name in allowed]
        state = ConversationState.from_messages(
            [
                get_delegate_system_prompt(),
                {"role": "user", "content": _build_delegate_prompt(request)},
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
                await on_event(
                    "trace.subagent_status",
                    {
                        "step_id": request.step_id,
                        "title": request.title,
                        "status": "completed",
                        "content": content,
                    },
                )
            elif event_type == "stream_start":
                await on_event(
                    "trace.subagent_status",
                    {
                        "step_id": request.step_id,
                        "title": request.title,
                        "status": "thinking",
                    },
                )
            elif event_type == "stream_thinking":
                await on_event(
                    "trace.subagent_thinking",
                    {
                        "step_id": request.step_id,
                        "title": request.title,
                        "content": content,
                    },
                )
            elif event_type == "stream_token":
                return
            elif event_type == "stream_end":
                return
            else:
                await on_event(
                    "trace.subagent_status",
                    {
                        "step_id": request.step_id,
                        "title": request.title,
                        "status": event_type,
                        "content": content,
                    },
                )

        result = await run_conversation(
            restricted_client,
            state,
            policy,
            inference,
            on_event=subagent_event,
        )
        parsed_result = _parse_delegate_result(
            request,
            result or "[sub-agent reached maximum iterations without completing]",
        )
        return parsed_result.to_json()

    return handle_delegate


def build_delegate_policy(registry, settings):
    from .policy import OrchestrationPolicy

    return OrchestrationPolicy(
        registry=registry,
        model_role="delegate",
        system_prompt=get_delegate_system_prompt(),
        max_rounds=settings.max_delegate_rounds,
    )
