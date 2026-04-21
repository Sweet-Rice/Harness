from typing import Protocol


class ConversationRepository(Protocol):
    def create_conversation(self, name: str) -> str:
        ...

    def list_conversations(self) -> list[dict]:
        ...

    def load_messages(self, conversation_id: str) -> list[dict] | None:
        ...

    def save_messages(self, conversation_id: str, messages: list[dict]) -> None:
        ...

    def delete_conversation(self, conversation_id: str) -> None:
        ...

    def rename_conversation(self, conversation_id: str, name: str) -> None:
        ...
