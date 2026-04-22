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


class PlanStore(Protocol):
    def create_workspace(
        self,
        name: str,
        *,
        thread_id: str,
        mode: str,
        source: str | None,
        client_id: str | None,
        initial_content: str,
    ):
        ...

    def list_workspaces(self):
        ...

    def get_workspace(self, workspace_id: str):
        ...

    def find_workspace_by_thread(self, thread_id: str, *, mode: str | None = None):
        ...

    def load_current_plan_state(self, workspace_id: str) -> str:
        ...

    def snapshot_ctrl(self, workspace_id: str, content: str) -> None:
        ...

    def update_in_use(
        self,
        workspace_id: str,
        new_content: str,
        *,
        reason: str,
        summary: str,
    ):
        ...
