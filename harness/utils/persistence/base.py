from typing import Protocol


class ConversationRepository(Protocol):
    def create_thread(
        self,
        name: str,
        *,
        thread_type: str,
        mode: str,
        source: str | None,
        client_id: str | None,
    ):
        ...

    def list_threads(
        self,
        *,
        source: str | None = None,
        client_id: str | None = None,
        include_global: bool = True,
    ):
        ...

    def get_thread(self, thread_id: str):
        ...

    def find_thread_by_identity(
        self,
        *,
        thread_type: str,
        source: str | None,
        client_id: str | None,
    ):
        ...

    def load_thread_messages(self, thread_id: str):
        ...

    def save_thread_messages(self, thread_id: str, messages) -> None:
        ...

    def delete_thread(self, thread_id: str) -> None:
        ...

    def rename_thread(self, thread_id: str, name: str) -> None:
        ...
