from __future__ import annotations

from harness.utils.context.models import ConversationThread
from harness.utils.persistence import SQLiteConversationRepository


class ConversationManager:
    def __init__(self, repository=None):
        self.repository = repository or SQLiteConversationRepository()
        self._current_thread_id = None

    @property
    def current(self):
        return self._current_thread_id

    def create_thread(
        self,
        name=None,
        *,
        thread_type="global_thread",
        mode="orchestrated",
        source=None,
        client_id=None,
    ):
        if name is None:
            count = len(self.repository.list_threads())
            name = f"Chat {count + 1}"
        thread = self.repository.create_thread(
            name,
            thread_type=thread_type,
            mode=mode,
            source=source,
            client_id=client_id,
        )
        self._current_thread_id = thread.id
        return thread

    def new(self, name=None, **kwargs):
        return self.create_thread(name, **kwargs).id

    def list(self, *, source=None, client_id=None, include_global=True):
        return [
            {
                "id": thread.id,
                "name": thread.name,
                "thread_type": thread.thread_type,
                "mode": thread.mode,
                "source": thread.source,
                "client_id": thread.client_id,
                "created_at": thread.created_at,
                "updated_at": thread.updated_at,
                "message_count": thread.message_count,
            }
            for thread in self.repository.list_threads(
                source=source,
                client_id=client_id,
                include_global=include_global,
            )
        ]

    def load_thread(self, thread_id) -> ConversationThread | None:
        thread = self.repository.get_thread(thread_id)
        if thread is None:
            return None
        messages = [message.to_dict() for message in self.repository.load_thread_messages(thread_id)]
        self._current_thread_id = thread_id
        return ConversationThread(thread=thread, messages=messages)

    def load(self, thread_id):
        loaded = self.load_thread(thread_id)
        if loaded is None:
            return None
        return loaded.messages

    def save(self, thread_id, messages):
        if thread_id is None:
            raise ValueError("Cannot save messages without an active thread")
        to_save = [dict(message) for message in messages if message.get("role") != "system"]
        self.repository.save_thread_messages(thread_id, to_save)

    def delete(self, thread_id):
        self.repository.delete_thread(thread_id)
        if self._current_thread_id == thread_id:
            self._current_thread_id = None

    def rename(self, thread_id, name):
        self.repository.rename_thread(thread_id, name)

    def get_or_create_client_scratch(
        self,
        *,
        source: str,
        client_id: str,
        name: str,
        mode: str = "orchestrated",
    ) -> ConversationThread:
        thread = self.repository.find_thread_by_identity(
            thread_type="client_scratch",
            source=source,
            client_id=client_id,
        )
        if thread is None:
            thread = self.create_thread(
                name,
                thread_type="client_scratch",
                mode=mode,
                source=source,
                client_id=client_id,
            )
        loaded = self.load_thread(thread.id)
        if loaded is None:
            raise ValueError(f"Unable to load thread {thread.id}")
        return loaded
