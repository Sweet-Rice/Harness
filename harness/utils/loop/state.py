from dataclasses import dataclass, field

from harness.utils.context.models import MessageRecord

from .response import serialize_tool_call


@dataclass
class ConversationState:
    messages: list[MessageRecord] = field(default_factory=list)

    @classmethod
    def from_messages(cls, messages: list[dict | MessageRecord]) -> "ConversationState":
        records = []
        for message in messages:
            if isinstance(message, MessageRecord):
                records.append(message)
            else:
                records.append(MessageRecord.from_dict(message))
        return cls(messages=records)

    def to_messages(self) -> list[dict]:
        return [message.to_dict() for message in self.messages]

    def to_model_messages(self) -> list[dict]:
        return [message.to_model_message() for message in self.messages]

    def ensure_system_message(self, system_message: dict | MessageRecord):
        if self.messages and self.messages[0].role == "system":
            return
        if isinstance(system_message, MessageRecord):
            self.messages.insert(0, system_message)
        else:
            self.messages.insert(0, MessageRecord.from_dict(system_message))

    def append_message(self, role: str, content: str, **extra):
        payload = {"role": role, "content": content}
        if extra:
            payload.update(extra)
        self.messages.append(MessageRecord.from_dict(payload))

    def append_assistant_with_tool_calls(self, content: str, tool_calls: list):
        self.messages.append(
            MessageRecord(
                role="assistant",
                content=content,
                message_type="assistant",
                tool_calls=[serialize_tool_call(tool_call) for tool_call in tool_calls],
            )
        )

    def append_tool_result(self, name: str, content: str):
        self.messages.append(
            MessageRecord(
                role="tool",
                content=content,
                message_type="tool_result",
                tool_name=name,
            )
        )
