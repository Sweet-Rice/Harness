from dataclasses import dataclass, field

from .response import serialize_tool_call


@dataclass
class ConversationState:
    messages: list[dict] = field(default_factory=list)

    @classmethod
    def from_messages(cls, messages: list[dict]) -> "ConversationState":
        return cls(messages=[dict(message) for message in messages])

    def to_messages(self) -> list[dict]:
        return self.messages

    def ensure_system_message(self, system_message: dict):
        if self.messages and self.messages[0].get("role") == "system":
            return
        self.messages.insert(0, dict(system_message))

    def append_message(self, role: str, content: str, **extra):
        message = {"role": role, "content": content}
        if extra:
            message.update(extra)
        self.messages.append(message)

    def append_assistant_with_tool_calls(self, content: str, tool_calls: list):
        self.messages.append(
            {
                "role": "assistant",
                "content": content,
                "tool_calls": [serialize_tool_call(tool_call) for tool_call in tool_calls],
            }
        )

    def append_tool_result(self, name: str, content: str):
        self.messages.append({"role": "tool", "content": content, "name": name})
