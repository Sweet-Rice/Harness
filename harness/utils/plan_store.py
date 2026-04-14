"""Plan file versioning on top of the persistence interface.

Terminology:
    ctrl    — immutable snapshot of the plan at creation time
    in_use  — live copy, modified during execution
    diff    — log entry recording each change to in_use
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from harness.utils.persistence import PersistenceBackend, new_id


@dataclass
class Plan:
    """Represents a plan with its current state."""

    id: str
    text: str
    status: str  # active, completed, failed, paused
    conversation_id: str
    ctrl_text: str  # original snapshot — never changes
    created_at: str
    updated_at: str


@dataclass
class Diff:
    """A single change record."""

    id: str
    plan_id: str
    before: str
    after: str
    description: str
    created_at: str


class PlanStore:
    """Plan file versioning using a PersistenceBackend."""

    PLANS = "plans"
    DIFFS = "plan_diffs"

    def __init__(self, backend: PersistenceBackend):
        self._db = backend

    def create(
        self,
        text: str,
        *,
        conversation_id: str = "",
        status: str = "active",
    ) -> Plan:
        """Create a new plan with a ctrl snapshot."""
        plan_id = new_id()
        ctrl_id = new_id()

        # Ctrl snapshot — immutable baseline
        self._db.write(
            self.PLANS,
            ctrl_id,
            {"text": text, "status": "ctrl"},
            metadata={"is_ctrl": True, "parent_plan_id": plan_id},
        )

        # In-use copy — mutable
        doc = self._db.write(
            self.PLANS,
            plan_id,
            {"text": text, "status": status},
            metadata={
                "conversation_id": conversation_id,
                "ctrl_id": ctrl_id,
                "is_ctrl": False,
            },
        )

        return Plan(
            id=plan_id,
            text=text,
            status=status,
            conversation_id=conversation_id,
            ctrl_text=text,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    def get(self, plan_id: str) -> Optional[Plan]:
        """Read a plan and its ctrl snapshot."""
        doc = self._db.read(self.PLANS, plan_id)
        if not doc or doc.metadata.get("is_ctrl"):
            return None

        ctrl_text = ""
        ctrl_id = doc.metadata.get("ctrl_id")
        if ctrl_id:
            ctrl_doc = self._db.read(self.PLANS, ctrl_id)
            if ctrl_doc:
                ctrl_text = ctrl_doc.data.get("text", "")

        return Plan(
            id=doc.id,
            text=doc.data.get("text", ""),
            status=doc.data.get("status", ""),
            conversation_id=doc.metadata.get("conversation_id", ""),
            ctrl_text=ctrl_text,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    def update(
        self,
        plan_id: str,
        new_text: str,
        description: str = "",
    ) -> Optional[Plan]:
        """Update a plan's text and append a diff."""
        doc = self._db.read(self.PLANS, plan_id)
        if not doc or doc.metadata.get("is_ctrl"):
            return None

        old_text = doc.data.get("text", "")

        # Append diff
        self._db.write(
            self.DIFFS,
            new_id(),
            {"before": old_text, "after": new_text, "description": description},
            metadata={"plan_id": plan_id},
        )

        # Update in_use
        self._db.write(
            self.PLANS,
            plan_id,
            {"text": new_text, "status": doc.data.get("status", "active")},
            metadata=doc.metadata,
        )

        return self.get(plan_id)

    def set_status(self, plan_id: str, status: str) -> Optional[Plan]:
        """Update a plan's status without creating a diff."""
        doc = self._db.read(self.PLANS, plan_id)
        if not doc or doc.metadata.get("is_ctrl"):
            return None

        self._db.write(
            self.PLANS,
            plan_id,
            {"text": doc.data.get("text", ""), "status": status},
            metadata=doc.metadata,
        )

        return self.get(plan_id)

    def get_diffs(self, plan_id: str) -> list[Diff]:
        """Get change history for a plan, ordered by time."""
        docs = self._db.query(
            self.DIFFS,
            filter_metadata={"plan_id": plan_id},
            order_by="created_at",
        )
        return [
            Diff(
                id=d.id,
                plan_id=plan_id,
                before=d.data.get("before", ""),
                after=d.data.get("after", ""),
                description=d.data.get("description", ""),
                created_at=d.created_at,
            )
            for d in docs
        ]

    def get_ctrl(self, plan_id: str) -> Optional[str]:
        """Get the original plan text (ctrl snapshot)."""
        doc = self._db.read(self.PLANS, plan_id)
        if not doc:
            return None
        ctrl_id = doc.metadata.get("ctrl_id")
        if not ctrl_id:
            return None
        ctrl_doc = self._db.read(self.PLANS, ctrl_id)
        if not ctrl_doc:
            return None
        return ctrl_doc.data.get("text", "")

    def list_plans(
        self,
        *,
        status: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> list[Plan]:
        """List plans, optionally filtered by status or conversation."""
        filter_meta: dict = {"is_ctrl": False}
        if conversation_id:
            filter_meta["conversation_id"] = conversation_id

        docs = self._db.query(
            self.PLANS,
            filter_metadata=filter_meta,
            order_by="updated_at",
        )

        plans = []
        for doc in docs:
            if status and doc.data.get("status") != status:
                continue

            ctrl_text = ""
            ctrl_id = doc.metadata.get("ctrl_id")
            if ctrl_id:
                ctrl_doc = self._db.read(self.PLANS, ctrl_id)
                if ctrl_doc:
                    ctrl_text = ctrl_doc.data.get("text", "")

            plans.append(
                Plan(
                    id=doc.id,
                    text=doc.data.get("text", ""),
                    status=doc.data.get("status", ""),
                    conversation_id=doc.metadata.get("conversation_id", ""),
                    ctrl_text=ctrl_text,
                    created_at=doc.created_at,
                    updated_at=doc.updated_at,
                )
            )

        return plans

    def delete(self, plan_id: str) -> bool:
        """Remove a plan, its ctrl snapshot, and all diffs."""
        doc = self._db.read(self.PLANS, plan_id)
        if not doc:
            return False

        # Delete diffs
        diffs = self._db.query(
            self.DIFFS, filter_metadata={"plan_id": plan_id}
        )
        for d in diffs:
            self._db.delete(self.DIFFS, d.id)

        # Delete ctrl
        ctrl_id = doc.metadata.get("ctrl_id")
        if ctrl_id:
            self._db.delete(self.PLANS, ctrl_id)

        # Delete plan
        return self._db.delete(self.PLANS, plan_id)
