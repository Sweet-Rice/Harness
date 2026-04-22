from __future__ import annotations

from collections.abc import Iterable

from harness.utils.inference import get_default_registry

from .prompts import get_chat_system_prompt


SKILL_DESCRIPTIONS = {
    "summarize_thread": (
        "Summarize the supplied conversation transcript, including major topics, "
        "decisions, and clear follow-up actions."
    ),
}


def available_skill_names() -> tuple[str, ...]:
    return tuple(SKILL_DESCRIPTIONS)


def skill_trigger_tool() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "trigger_skill",
            "description": (
                "Run a named skill on the supplied payload. Skills are higher-level "
                "intent actions and are not the same thing as raw tool access."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": (
                            "The skill to run. Available skills: "
                            + ", ".join(available_skill_names())
                        ),
                    },
                    "payload": {
                        "type": "string",
                        "description": "The input text for the skill.",
                    },
                    "client_type": {
                        "type": "string",
                        "description": "Optional client context such as web or discord.",
                    },
                },
                "required": ["skill_name", "payload"],
            },
        },
    }


def _render_transcript(messages: Iterable[dict]) -> str:
    lines: list[str] = []
    for message in messages:
        role = message.get("role", "message")
        content = message.get("content", "")
        if not content:
            continue
        if role == "tool":
            tool_name = message.get("tool_name") or message.get("name") or "tool"
            lines.append(f"[tool:{tool_name}] {content}")
        else:
            lines.append(f"[{role}] {content}")
    return "\n".join(lines)


def build_skill_payload(skill_name: str, messages: Iterable[dict]) -> str:
    transcript = _render_transcript(messages)
    if not transcript:
        return ""
    if skill_name == "summarize_thread":
        return transcript
    return transcript


async def execute_skill(
    skill_name: str,
    payload: str,
    *,
    client_type: str,
    registry=None,
    on_event=None,
) -> str:
    if skill_name not in SKILL_DESCRIPTIONS:
        available = ", ".join(available_skill_names()) or "none"
        return f"Unknown skill '{skill_name}'. Available skills: {available}"

    registry = registry or get_default_registry()
    prompt = (
        "You are executing a named skill for the Harness assistant.\n"
        f"Client: {client_type}\n"
        f"Skill: {skill_name}\n\n"
        "Return only the skill result. Do not mention internal policies.\n\n"
        "Payload:\n"
        f"{payload}"
    )

    inference = registry.get_client()
    model = registry.model_for("chat")
    chunks: list[str] = []
    async for chunk in inference.stream_chat(
        model=model,
        messages=[
            get_chat_system_prompt(),
            {"role": "user", "content": prompt},
        ],
        tools=None,
        think=False,
    ):
        if chunk.thinking and on_event:
            await on_event("stream_thinking", chunk.thinking)
        if chunk.content:
            chunks.append(chunk.content)
            if on_event:
                await on_event("stream_token", chunk.content)
    return "".join(chunks).strip()


def build_skill_handler(registry):
    async def handle_skill(client, args, on_event=None):
        return await execute_skill(
            args["skill_name"],
            args["payload"],
            client_type=args.get("client_type") or "orchestrator",
            registry=registry,
            on_event=on_event,
        )

    return handle_skill
