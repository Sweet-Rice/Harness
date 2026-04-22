from __future__ import annotations

from dataclasses import dataclass

from harness.utils.persistence import FilePlanStore

from .plan_model import (
    DelegatedStepResult,
    PlanDocument,
    PlanStep,
    PlanStepResult,
    looks_like_structured_plan,
    parse_plan_markdown,
    render_plan_markdown,
)


RECENT_NOTES_LIMIT = 6


@dataclass
class OrchestratedRunSession:
    thread_id: str
    workspace_id: str
    mode: str
    source: str | None
    client_id: str | None
    thread_name: str


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).strip()


def _truncate_title(text: str, *, limit: int = 72) -> str:
    cleaned = _normalize_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _latest_message_content(messages: list[dict], role: str) -> str | None:
    for message in reversed(messages):
        if message.get("role") == role and message.get("content"):
            return str(message["content"]).strip()
    return None


def _latest_delegate_result(messages: list[dict]) -> DelegatedStepResult | None:
    for message in reversed(messages):
        if message.get("role") == "user":
            break
        if message.get("role") != "tool":
            continue
        tool_name = message.get("tool_name") or message.get("name")
        if tool_name != "delegate_agent":
            continue
        content = message.get("content", "")
        try:
            return DelegatedStepResult(**parse_delegate_json(content))
        except Exception:
            return None
    return None


def parse_delegate_json(payload: str) -> dict:
    from .plan_model import delegated_result_from_json

    result = delegated_result_from_json(payload)
    return {
        "step_id": result.step_id,
        "status": result.status,
        "summary": result.summary,
        "artifacts": result.artifacts,
        "follow_up_note": result.follow_up_note,
        "failure_reason": result.failure_reason,
    }


def _plan_context_message(plan: PlanDocument) -> dict:
    active_step = next((step for step in plan.steps if step.step_id == plan.active_step_id), None)
    completed = [step for step in plan.steps if step.status == "completed"][-3:]
    blocked = [step for step in plan.steps if step.status in {"blocked", "failed"}][-2:]

    lines = [
        "Plan state is canonical for this orchestrated task.",
        "Use the plan-derived context below as the authoritative task state. Conversation history is only a mirror for the user.",
        "",
        f"Objective: {plan.objective}",
        f"Overall status: {plan.overall_status}",
    ]
    if active_step is not None:
        lines.extend(
            [
                "",
                f"Active step: {active_step.step_id} - {active_step.title}",
                f"Active step summary: {active_step.summary}",
                f"Allowed tools hint: {', '.join(active_step.allowed_tools) or 'any currently exposed tool'}",
                f"Latest step note: {active_step.latest_note or 'none'}",
            ]
        )
    if completed:
        lines.extend(["", "Recently completed:"])
        lines.extend(f"- {step.step_id}: {step.title}" for step in completed)
    if blocked:
        lines.extend(["", "Recently blocked or failed:"])
        lines.extend(f"- {step.step_id}: {step.latest_note or step.title}" for step in blocked)
    if plan.recent_notes:
        lines.extend(["", "Recent execution notes:"])
        lines.extend(f"- {note}" for note in plan.recent_notes[-3:])

    return {
        "role": "system",
        "content": "\n".join(lines),
        "metadata": {"plan_state": True},
    }


class OrchestratedRunService:
    def __init__(self, plan_store: FilePlanStore | None = None):
        self.plan_store = plan_store or FilePlanStore()

    def load_or_create_session(self, thread, messages: list[dict]) -> OrchestratedRunSession:
        metadata = self.plan_store.find_workspace_by_thread(thread.id, mode=thread.mode)
        if metadata is None:
            plan = self._build_initial_plan(
                thread_name=thread.name,
                thread_id=thread.id,
                mode=thread.mode,
                source=thread.source,
                client_id=thread.client_id,
                messages=messages,
            )
            metadata = self.plan_store.create_workspace(
                thread.name,
                thread_id=thread.id,
                mode=thread.mode,
                source=thread.source,
                client_id=thread.client_id,
                initial_content=render_plan_markdown(plan),
            )
        else:
            workspace = self.plan_store.get_workspace(metadata.id)
            needs_rebuild = not looks_like_structured_plan(workspace.in_use_content)
            if not needs_rebuild:
                try:
                    parse_plan_markdown(workspace.in_use_content)
                except Exception:
                    needs_rebuild = True
            if needs_rebuild:
                self.plan_store.delete_workspace(metadata.id)
                plan = self._build_initial_plan(
                    thread_name=thread.name,
                    thread_id=thread.id,
                    mode=thread.mode,
                    source=thread.source,
                    client_id=thread.client_id,
                    messages=messages,
                )
                metadata = self.plan_store.create_workspace(
                    thread.name,
                    thread_id=thread.id,
                    mode=thread.mode,
                    source=thread.source,
                    client_id=thread.client_id,
                    initial_content=render_plan_markdown(plan),
                )
        return OrchestratedRunSession(
            thread_id=thread.id,
            workspace_id=metadata.id,
            mode=metadata.mode,
            source=metadata.source,
            client_id=metadata.client_id,
            thread_name=metadata.name,
        )

    def load_plan(self, session: OrchestratedRunSession) -> PlanDocument:
        return parse_plan_markdown(self.plan_store.load_current_plan_state(session.workspace_id))

    def build_runtime_messages(
        self,
        session: OrchestratedRunSession,
        messages: list[dict],
    ) -> list[dict]:
        plan = self.load_plan(session)
        return [_plan_context_message(plan), *[dict(message) for message in messages]]

    async def sync_before_turn(
        self,
        session: OrchestratedRunSession,
        messages: list[dict],
        *,
        on_event=None,
    ) -> PlanDocument:
        plan = self.load_plan(session)
        latest_user = _latest_message_content(messages, "user")
        if latest_user:
            self._ensure_step_for_latest_user(plan, latest_user)
        self._select_active_step(plan)
        plan.overall_status = "in_progress" if plan.active_step_id else "awaiting_input"
        if latest_user:
            self._append_recent_note(plan, f"User requested: {_truncate_title(latest_user, limit=120)}")
        saved = self._save_plan(
            session,
            plan,
            reason="user_turn",
            summary="Prepared structured plan state before the orchestrator turn.",
        )
        if on_event:
            await on_event("trace.plan_update", self.plan_trace_payload(saved))
        return saved

    async def sync_after_turn(
        self,
        session: OrchestratedRunSession,
        messages: list[dict],
        *,
        on_event=None,
    ) -> PlanDocument:
        plan = self.load_plan(session)
        delegate_result = _latest_delegate_result(messages)
        latest_assistant = _latest_message_content(messages, "assistant") or ""

        if delegate_result is not None:
            self._apply_delegated_result(plan, delegate_result)
        elif plan.active_step_id is not None:
            self._apply_step_result(
                plan,
                PlanStepResult(
                    step_id=plan.active_step_id,
                    status="completed",
                    summary=_truncate_title(latest_assistant or "Assistant completed the active step.", limit=160),
                ),
            )

        plan.latest_assistant_summary = latest_assistant or plan.latest_assistant_summary
        plan.active_step_id = None
        self._select_active_step(plan)
        plan.overall_status = "in_progress" if plan.active_step_id else "awaiting_input"
        if latest_assistant:
            self._append_recent_note(plan, f"Assistant summary: {_truncate_title(latest_assistant, limit=120)}")
        saved = self._save_plan(
            session,
            plan,
            reason="assistant_turn",
            summary="Applied structured orchestration results back into canonical plan state.",
        )
        if on_event:
            await on_event("trace.plan_update", self.plan_trace_payload(saved))
        return saved

    def delete_for_thread(self, thread_id: str, *, mode: str | None = None) -> None:
        metadata = self.plan_store.find_workspace_by_thread(thread_id, mode=mode)
        if metadata is None:
            return
        self.plan_store.delete_workspace(metadata.id)

    def plan_trace_payload(self, plan: PlanDocument) -> dict:
        return {
            "title": plan.title,
            "objective": plan.objective,
            "overall_status": plan.overall_status,
            "active_step_id": plan.active_step_id,
            "steps": [
                {
                    "step_id": step.step_id,
                    "title": step.title,
                    "status": step.status,
                    "owner": step.owner,
                    "latest_note": step.latest_note,
                }
                for step in plan.steps
            ],
            "recent_notes": list(plan.recent_notes),
            "latest_assistant_summary": plan.latest_assistant_summary,
        }

    def _save_plan(
        self,
        session: OrchestratedRunSession,
        plan: PlanDocument,
        *,
        reason: str,
        summary: str,
    ) -> PlanDocument:
        plan.title = session.thread_name
        rendered = render_plan_markdown(plan)
        workspace = self.plan_store.update_in_use(
            session.workspace_id,
            rendered,
            reason=reason,
            summary=summary,
        )
        return parse_plan_markdown(workspace.in_use_content)

    def _build_initial_plan(
        self,
        *,
        thread_name: str,
        thread_id: str,
        mode: str,
        source: str | None,
        client_id: str | None,
        messages: list[dict],
    ) -> PlanDocument:
        latest_user = _latest_message_content(messages, "user") or "Await the first user request."
        first_step = PlanStep(
            step_id="step-1",
            title=_truncate_title(latest_user, limit=72) or "Respond to the first user request",
            summary=_normalize_text(latest_user),
            latest_note="Created from the latest user request.",
        )
        return PlanDocument(
            title=thread_name,
            thread_id=thread_id,
            mode=mode,
            source=source,
            client_id=client_id,
            overall_status="awaiting_input",
            objective=_normalize_text(latest_user),
            active_step_id=None,
            steps=[first_step],
            recent_notes=[],
            latest_assistant_summary="",
        )

    def _next_step_id(self, plan: PlanDocument) -> str:
        return f"step-{len(plan.steps) + 1}"

    def _ensure_step_for_latest_user(self, plan: PlanDocument, latest_user: str) -> None:
        normalized = _normalize_text(latest_user)
        if not normalized:
            return
        plan.objective = normalized
        if plan.steps and plan.steps[-1].summary == normalized:
            return
        if any(step.status == "in_progress" for step in plan.steps):
            return
        plan.steps.append(
            PlanStep(
                step_id=self._next_step_id(plan),
                title=_truncate_title(normalized, limit=72) or "Address latest user request",
                summary=normalized,
                latest_note="Queued from the latest user request.",
            )
        )

    def _select_active_step(self, plan: PlanDocument) -> None:
        active = next((step for step in plan.steps if step.status == "in_progress"), None)
        if active is not None:
            plan.active_step_id = active.step_id
            return
        pending = next((step for step in plan.steps if step.status == "pending"), None)
        if pending is None:
            plan.active_step_id = None
            return
        pending.status = "in_progress"
        pending.latest_note = pending.latest_note or "Marked active for the next orchestrator turn."
        plan.active_step_id = pending.step_id

    def _apply_step_result(self, plan: PlanDocument, result: PlanStepResult) -> None:
        step = next((item for item in plan.steps if item.step_id == result.step_id), None)
        if step is None:
            return
        step.status = result.status
        step.latest_note = result.follow_up_note or result.failure_reason or result.summary
        if result.summary:
            step.summary = step.summary or result.summary

    def _apply_delegated_result(self, plan: PlanDocument, result: DelegatedStepResult) -> None:
        step = next((item for item in plan.steps if item.step_id == result.step_id), None)
        if step is None and plan.active_step_id is not None:
            step = next((item for item in plan.steps if item.step_id == plan.active_step_id), None)
        if step is None:
            return
        step.owner = "delegate"
        step.status = result.status
        step.latest_note = (
            result.follow_up_note
            or result.failure_reason
            or result.summary
        )
        if result.summary:
            step.summary = step.summary or result.summary
        artifacts = ", ".join(result.artifacts)
        note = f"Delegate result for {step.step_id}: {result.summary}"
        if artifacts:
            note += f" Artifacts: {artifacts}"
        self._append_recent_note(plan, note)
        plan.active_step_id = None

    def _append_recent_note(self, plan: PlanDocument, note: str) -> None:
        cleaned = _normalize_text(note)
        if not cleaned:
            return
        if plan.recent_notes and plan.recent_notes[-1] == cleaned:
            return
        plan.recent_notes.append(cleaned)
        del plan.recent_notes[:-RECENT_NOTES_LIMIT]
