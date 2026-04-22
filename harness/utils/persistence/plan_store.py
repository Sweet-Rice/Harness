from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from difflib import unified_diff
from pathlib import Path

from harness.utils.config import SETTINGS


PLAN_MANIFEST = "manifest.json"
CTRL_PLAN = "ctrl.md"
IN_USE_PLAN = "in_use.md"
DIFF_LOG = "diffs.ndjson"


def _utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


@dataclass
class PlanWorkspaceMetadata:
    id: str
    name: str
    thread_id: str
    mode: str
    source: str | None
    client_id: str | None
    created_at: str
    updated_at: str


@dataclass
class PlanWorkspace:
    metadata: PlanWorkspaceMetadata
    ctrl_content: str
    in_use_content: str


class FilePlanStore:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root or SETTINGS.plan_store_path)
        self.root.mkdir(parents=True, exist_ok=True)

    def _workspace_dir(self, workspace_id: str) -> Path:
        return self.root / workspace_id

    def _read_metadata(self, workspace_id: str) -> PlanWorkspaceMetadata:
        data = json.loads((self._workspace_dir(workspace_id) / PLAN_MANIFEST).read_text())
        return PlanWorkspaceMetadata(**data)

    def _write_metadata(self, metadata: PlanWorkspaceMetadata) -> None:
        workspace_dir = self._workspace_dir(metadata.id)
        workspace_dir.mkdir(parents=True, exist_ok=True)
        (workspace_dir / PLAN_MANIFEST).write_text(
            json.dumps(asdict(metadata), indent=2) + "\n"
        )

    def _append_diff(
        self,
        workspace_id: str,
        *,
        previous_content: str,
        new_content: str,
        reason: str,
        summary: str,
    ) -> None:
        diff_lines = list(
            unified_diff(
                previous_content.splitlines(),
                new_content.splitlines(),
                fromfile=CTRL_PLAN,
                tofile=IN_USE_PLAN,
                lineterm="",
            )
        )
        entry = {
            "timestamp": _utc_now(),
            "reason": reason,
            "summary": summary,
            "diff": "\n".join(diff_lines),
        }
        with (self._workspace_dir(workspace_id) / DIFF_LOG).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def create_workspace(
        self,
        name: str,
        *,
        thread_id: str,
        mode: str,
        source: str | None,
        client_id: str | None,
        initial_content: str,
    ) -> PlanWorkspaceMetadata:
        workspace_id = uuid.uuid4().hex[:12]
        created_at = _utc_now()
        metadata = PlanWorkspaceMetadata(
            id=workspace_id,
            name=name,
            thread_id=thread_id,
            mode=mode,
            source=source,
            client_id=client_id,
            created_at=created_at,
            updated_at=created_at,
        )
        workspace_dir = self._workspace_dir(workspace_id)
        workspace_dir.mkdir(parents=True, exist_ok=True)
        self._write_metadata(metadata)
        (workspace_dir / CTRL_PLAN).write_text(initial_content, encoding="utf-8")
        (workspace_dir / IN_USE_PLAN).write_text(initial_content, encoding="utf-8")
        (workspace_dir / DIFF_LOG).write_text("", encoding="utf-8")
        return metadata

    def list_workspaces(self) -> list[PlanWorkspaceMetadata]:
        workspaces: list[PlanWorkspaceMetadata] = []
        for manifest in sorted(self.root.glob(f"*/{PLAN_MANIFEST}")):
            workspaces.append(PlanWorkspaceMetadata(**json.loads(manifest.read_text())))
        workspaces.sort(key=lambda workspace: workspace.updated_at, reverse=True)
        return workspaces

    def get_workspace(self, workspace_id: str) -> PlanWorkspace:
        metadata = self._read_metadata(workspace_id)
        workspace_dir = self._workspace_dir(workspace_id)
        return PlanWorkspace(
            metadata=metadata,
            ctrl_content=(workspace_dir / CTRL_PLAN).read_text(encoding="utf-8"),
            in_use_content=(workspace_dir / IN_USE_PLAN).read_text(encoding="utf-8"),
        )

    def find_workspace_by_thread(
        self,
        thread_id: str,
        *,
        mode: str | None = None,
    ) -> PlanWorkspaceMetadata | None:
        for metadata in self.list_workspaces():
            if metadata.thread_id != thread_id:
                continue
            if mode is not None and metadata.mode != mode:
                continue
            return metadata
        return None

    def load_current_plan_state(self, workspace_id: str) -> str:
        return (self._workspace_dir(workspace_id) / IN_USE_PLAN).read_text(encoding="utf-8")

    def snapshot_ctrl(self, workspace_id: str, content: str) -> None:
        ctrl_path = self._workspace_dir(workspace_id) / CTRL_PLAN
        if ctrl_path.exists() and ctrl_path.read_text(encoding="utf-8"):
            raise ValueError(f"ctrl snapshot already exists for workspace {workspace_id}")
        ctrl_path.write_text(content, encoding="utf-8")

    def update_in_use(
        self,
        workspace_id: str,
        new_content: str,
        *,
        reason: str,
        summary: str,
    ) -> PlanWorkspace:
        workspace_dir = self._workspace_dir(workspace_id)
        in_use_path = workspace_dir / IN_USE_PLAN
        previous_content = in_use_path.read_text(encoding="utf-8")
        if previous_content != new_content:
            self._append_diff(
                workspace_id,
                previous_content=previous_content,
                new_content=new_content,
                reason=reason,
                summary=summary,
            )
            in_use_path.write_text(new_content, encoding="utf-8")

        metadata = self._read_metadata(workspace_id)
        metadata.updated_at = _utc_now()
        self._write_metadata(metadata)
        return self.get_workspace(workspace_id)

    def delete_workspace(self, workspace_id: str) -> None:
        workspace_dir = self._workspace_dir(workspace_id)
        if not workspace_dir.exists():
            return
        for child in workspace_dir.iterdir():
            child.unlink()
        workspace_dir.rmdir()
