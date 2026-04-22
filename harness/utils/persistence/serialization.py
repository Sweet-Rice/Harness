from __future__ import annotations

from harness.utils.context.models import MessageRecord


def deserialize_messages(rows) -> list[MessageRecord]:
    messages: list[MessageRecord] = []
    for row in rows:
        payload = {
            "role": row["role"],
            "content": row["content"],
            "message_type": row["message_type"],
            "tool_name": row["tool_name"],
            "source": row["source"],
            "tool_calls": row["tool_calls"] or [],
            "metadata": row["metadata"] or {},
        }
        messages.append(MessageRecord.from_dict(payload))
    return messages


def serialize_messages(messages: list[MessageRecord | dict]) -> list[MessageRecord]:
    serialized: list[MessageRecord] = []
    for message in messages:
        if isinstance(message, MessageRecord):
            serialized.append(message)
        elif isinstance(message, dict):
            serialized.append(MessageRecord.from_dict(message))
        else:
            raise ValueError(f"Unsupported message type: {type(message)!r}")
    return serialized
