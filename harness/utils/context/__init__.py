from harness.utils.orchestration.prompts import get_orchestrator_system_prompt
from harness.utils.persistence import SQLiteConversationRepository


class ConversationManager:
    def __init__(self, repository=None):
        self.repository = repository or SQLiteConversationRepository()
        self._current = None

    @property
    def current(self):
        return self._current

    def new(self, name=None):
        if name is None:
            count = len(self.repository.list_conversations())
            name = f"Chat {count + 1}"
        cid = self.repository.create_conversation(name)
        self._current = cid
        return cid

    def list(self):
        return self.repository.list_conversations()

    def load(self, conversation_id):
        messages = self.repository.load_messages(conversation_id)
        if messages is None:
            return None
        self._current = conversation_id
        return [get_orchestrator_system_prompt(), *messages]

    def save(self, conversation_id, messages):
        to_save = [dict(message) for message in messages if message.get("role") != "system"]
        self.repository.save_messages(conversation_id, to_save)

    def delete(self, conversation_id):
        self.repository.delete_conversation(conversation_id)
        if self._current == conversation_id:
            self._current = None

    def rename(self, conversation_id, name):
        self.repository.rename_conversation(conversation_id, name)
