from pathlib import Path

from harness.config import load_config
from harness.utils.persistence import SQLiteBackend
from harness.utils.plan_store import PlanStore


_config = load_config()
_db_path = Path(_config.db_path) if _config.db_path else Path(__file__).parent.parent / "harness.db"
_backend = SQLiteBackend(_db_path)
_plans = PlanStore(_backend)


def create_plan(text: str, conversation_id: str = "") -> str:
    """Create a new execution plan. Returns the plan ID and contents."""
    plan = _plans.create(text, conversation_id=conversation_id)
    return f"Plan created (id: {plan.id})\nStatus: {plan.status}\n\n{plan.text}"


def get_plan(plan_id: str) -> str:
    """Read the current state of a plan by its ID."""
    plan = _plans.get(plan_id)
    if not plan:
        return f"Error: plan '{plan_id}' not found"
    return f"Plan: {plan.id}\nStatus: {plan.status}\nCreated: {plan.created_at}\nUpdated: {plan.updated_at}\n\n{plan.text}"


def update_plan(plan_id: str, new_text: str, description: str = "") -> str:
    """Update a plan's text. Appends a diff for auditability."""
    plan = _plans.update(plan_id, new_text, description)
    if not plan:
        return f"Error: plan '{plan_id}' not found"
    return f"Plan updated (id: {plan.id})\nStatus: {plan.status}\n\n{plan.text}"


def set_plan_status(plan_id: str, status: str) -> str:
    """Set a plan's status (active, completed, failed, paused)."""
    plan = _plans.set_status(plan_id, status)
    if not plan:
        return f"Error: plan '{plan_id}' not found"
    return f"Plan {plan.id} status set to: {plan.status}"


def list_plans(status: str = "", conversation_id: str = "") -> str:
    """List all plans, optionally filtered by status or conversation."""
    plans = _plans.list_plans(
        status=status or None,
        conversation_id=conversation_id or None,
    )
    if not plans:
        return "No plans found"
    lines = []
    for p in plans:
        preview = p.text[:80].replace("\n", " ")
        lines.append(f"- {p.id} [{p.status}] {preview}...")
    return "\n".join(lines)


def get_plan_diffs(plan_id: str) -> str:
    """Get the change history for a plan."""
    diffs = _plans.get_diffs(plan_id)
    if not diffs:
        return f"No changes recorded for plan '{plan_id}'"
    lines = []
    for i, d in enumerate(diffs, 1):
        lines.append(f"--- Change {i} ({d.created_at}) ---")
        if d.description:
            lines.append(f"Description: {d.description}")
        lines.append(f"Before:\n{d.before}")
        lines.append(f"After:\n{d.after}")
        lines.append("")
    return "\n".join(lines)


TOOLS = [create_plan, get_plan, update_plan, set_plan_status, list_plans, get_plan_diffs]
