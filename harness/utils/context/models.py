from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ALLOWED_MESSAGE_KEYS = {
    "role",
    "content",
    "message_type",
    "tool_calls",
    "tool_name",
    "name",
    "source",
    "metadata",
}


@dataclass
class MessageRecord:
    role: str
    content: str
    message_type: str = "message"
    tool_calls: list[dict] = field(default_factory=list)
    tool_name: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MessageRecord":
        unknown = set(payload) - ALLOWED_MESSAGE_KEYS
        if unknown:
            raise ValueError(f"Unexpected message keys: {sorted(unknown)}")

        tool_name = payload.get("tool_name", payload.get("name"))
        tool_calls = payload.get("tool_calls") or []
        metadata = payload.get("metadata") or {}

        if not isinstance(metadata, dict):
            raise ValueError("Message metadata must be a dictionary")
        if not isinstance(tool_calls, list):
            raise ValueError("tool_calls must be a list")

        return cls(
            role=str(payload.get("role", "")),
            content=str(payload.get("content", "")),
            message_type=str(payload.get("message_type") or payload.get("role") or "message"),
            tool_calls=[dict(tool_call) for tool_call in tool_calls],
            tool_name=str(tool_name) if tool_name is not None else None,
            source=str(payload.get("source")) if payload.get("source") is not None else None,
            metadata=dict(metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "role": self.role,
            "content": self.content,
            "message_type": self.message_type,
        }
        if self.tool_calls:
            payload["tool_calls"] = [dict(tool_call) for tool_call in self.tool_calls]
        if self.tool_name:
            payload["tool_name"] = self.tool_name
        if self.source:
            payload["source"] = self.source
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload

    def to_model_message(self) -> dict[str, Any]:
        payload = {
            "role": self.role,
            "content": self.content,
        }
        if self.tool_calls:
            payload["tool_calls"] = [dict(tool_call) for tool_call in self.tool_calls]
        if self.tool_name:
            payload["name"] = self.tool_name
        return payload


@dataclass
class ThreadRecord:
    id: str
    name: str
    thread_type: str
    mode: str
    source: str | None
    client_id: str | None
    created_at: str
    updated_at: str
    message_count: int = 0


@dataclass
class ConversationThread:
    thread: ThreadRecord
    messages: list[dict]
