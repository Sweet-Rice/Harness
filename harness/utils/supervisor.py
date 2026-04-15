"""Supervisor: runs the orchestrator loop with context-switching delegation.

When the orchestrator calls run_agent, the loop returns a DelegationRequest.
The supervisor:
  1. Saves orchestrator messages to mmap (frees Python heap)
  2. Runs the agent in its own loop
  3. Restores orchestrator messages from mmap
  4. Appends the agent's output as a tool response
  5. Resumes the orchestrator
"""

import json
import re
from pathlib import Path

from harness.utils.agents import get_agent
from harness.utils.context_store import ContextStore
from harness.utils.llm import loop, DelegationRequest


CONTEXT_PATH = Path("/tmp/harness_context.mmap")


def _extract_plan_id(task: str) -> str | None:
    """Best-effort extraction for prompts like 'Execute plan abc123: ...'."""
    match = re.search(r"\bplan\s+([A-Za-z0-9_-]+)\b", task, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1)


def _parse_plan_status(plan_text: str) -> str:
    match = re.search(r"^Status:\s*(.+)$", plan_text, flags=re.MULTILINE)
    return match.group(1).strip() if match else "unknown"


def _verification_outcome(plan_status: str, plan_before: str, plan_after: str) -> str:
    if plan_status == "completed":
        return "verified_completed"
    if plan_status == "failed":
        return "verified_failed"
    if plan_status in {"active", "paused", "unknown"}:
        if plan_before == plan_after:
            return "unverified_unchanged"
        return "unverified_incomplete"
    return "unverified"


async def run(client, messages, on_event):
    """Run the orchestrator with context-switching agent delegation."""
    store = ContextStore(CONTEXT_PATH)

    try:
        while True:
            result = await loop(client, messages, on_event)

            if not isinstance(result, DelegationRequest):
                break

            plan_id = _extract_plan_id(result.task)
            plan_before = ""
            if plan_id:
                before_result = await client.call_tool("get_plan", {"plan_id": plan_id})
                plan_before = str(before_result.data)

            # Context switch: save orchestrator, free heap
            store.save("orchestrator", messages)
            messages.clear()

            # Spawn agent
            agent = get_agent(result.agent_name)
            await on_event("status", f"agent:{agent.name}")
            await on_event("agent_start", json.dumps({
                "agent_name": agent.name,
                "task": result.task,
                "role": agent.role,
                "allowed_tools": agent.allowed_tools,
            }))

            agent_messages = [
                {"role": "system", "content": agent.system_prompt},
                {"role": "user", "content": result.task},
            ]

            async def scoped_event(event_type, content):
                await on_event("agent_event", json.dumps({
                    "agent_name": agent.name,
                    "event_type": event_type,
                    "content": content,
                }))

            await loop(
                client,
                agent_messages,
                scoped_event,
                role=agent.role,
                allowed_tools=agent.allowed_tools,
            )

            # Capture agent output
            agent_output = agent_messages[-1].get("content", "")
            agent_messages.clear()

            plan_after = ""
            plan_status = "not_applicable"
            verification = {
                "plan_id": plan_id,
                "plan_status": plan_status,
                "outcome": "not_applicable",
                "plan_changed": False,
                "plan_before": "",
                "plan_after": "",
            }

            if plan_id:
                after_result = await client.call_tool("get_plan", {"plan_id": plan_id})
                plan_after = str(after_result.data)
                plan_status = _parse_plan_status(plan_after)

                verification = {
                    "plan_id": plan_id,
                    "plan_status": plan_status,
                    "outcome": _verification_outcome(plan_status, plan_before, plan_after),
                    "plan_changed": plan_before != plan_after,
                    "plan_before": plan_before,
                    "plan_after": plan_after,
                }

            await on_event("agent_end", json.dumps({
                "agent_name": agent.name,
                "output_preview": agent_output[:500],
                "verification": verification["outcome"],
            }))

            # Restore orchestrator from mmap
            restored = store.load("orchestrator")
            if restored:
                messages.extend(restored)
            tool_payload = {
                "agent_name": agent.name,
                "task": result.task,
                "output": agent_output,
                "verification": verification,
            }
            messages.append({"role": "tool", "content": json.dumps(tool_payload)})

            await on_event("status", "cooking")
    finally:
        store.close()
