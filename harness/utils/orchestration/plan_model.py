from __future__ import annotations

from dataclasses import dataclass, field
import json
import re


STEP_STATUSES = {"pending", "in_progress", "completed", "blocked", "failed"}


def _normalize_line(value: str) -> str:
    return " ".join(str(value).split()).strip()


def _parse_bullet_value(line: str, expected_key: str) -> str:
    prefix = f"- {expected_key}:"
    if not line.startswith(prefix):
        raise ValueError(f"Expected bullet '{expected_key}' in line: {line!r}")
    return line[len(prefix) :].strip()


@dataclass
class PlanStep:
    step_id: str
    title: str
    status: str = "pending"
    owner: str = "orchestrator"
    summary: str = ""
    allowed_tools: list[str] = field(default_factory=list)
    latest_note: str = ""

    def __post_init__(self):
        if self.status not in STEP_STATUSES:
            raise ValueError(f"Unsupported step status: {self.status}")
        self.title = _normalize_line(self.title)
        self.summary = _normalize_line(self.summary)
        self.latest_note = _normalize_line(self.latest_note)
        self.owner = _normalize_line(self.owner) or "orchestrator"
        self.allowed_tools = [tool for tool in (_normalize_line(tool) for tool in self.allowed_tools) if tool]


@dataclass
class PlanDocument:
    title: str
    thread_id: str
    mode: str
    source: str | None
    client_id: str | None
    overall_status: str
    objective: str
    active_step_id: str | None
    steps: list[PlanStep] = field(default_factory=list)
    recent_notes: list[str] = field(default_factory=list)
    latest_assistant_summary: str = ""


@dataclass
class PlanStepResult:
    step_id: str
    status: str
    summary: str
    artifacts: list[str] = field(default_factory=list)
    follow_up_note: str | None = None
    failure_reason: str | None = None

    def __post_init__(self):
        if self.status not in STEP_STATUSES:
            raise ValueError(f"Unsupported step result status: {self.status}")
        self.summary = _normalize_line(self.summary)
        self.artifacts = [artifact for artifact in (_normalize_line(a) for a in self.artifacts) if artifact]
        if self.follow_up_note is not None:
            self.follow_up_note = _normalize_line(self.follow_up_note)
        if self.failure_reason is not None:
            self.failure_reason = _normalize_line(self.failure_reason)


@dataclass
class DelegatedStepRequest:
    step_id: str
    title: str
    summary: str
    allowed_tools: list[str] = field(default_factory=list)
    execution_context: str = ""


@dataclass
class DelegatedStepResult:
    step_id: str
    status: str
    summary: str
    artifacts: list[str] = field(default_factory=list)
    follow_up_note: str | None = None
    failure_reason: str | None = None

    def __post_init__(self):
        if self.status not in STEP_STATUSES:
            raise ValueError(f"Unsupported delegated step status: {self.status}")
        self.summary = _normalize_line(self.summary)
        self.artifacts = [artifact for artifact in (_normalize_line(a) for a in self.artifacts) if artifact]
        if self.follow_up_note is not None:
            self.follow_up_note = _normalize_line(self.follow_up_note)
        if self.failure_reason is not None:
            self.failure_reason = _normalize_line(self.failure_reason)

    def to_json(self) -> str:
        return json.dumps(
            {
                "step_id": self.step_id,
                "status": self.status,
                "summary": self.summary,
                "artifacts": list(self.artifacts),
                "follow_up_note": self.follow_up_note,
                "failure_reason": self.failure_reason,
            },
            indent=2,
        )


def delegated_result_from_json(payload: str) -> DelegatedStepResult:
    data = json.loads(payload)
    return DelegatedStepResult(
        step_id=str(data["step_id"]),
        status=str(data["status"]),
        summary=str(data["summary"]),
        artifacts=[str(item) for item in data.get("artifacts", [])],
        follow_up_note=str(data["follow_up_note"]) if data.get("follow_up_note") is not None else None,
        failure_reason=str(data["failure_reason"]) if data.get("failure_reason") is not None else None,
    )


def render_plan_markdown(plan: PlanDocument) -> str:
    lines = [
        f"# Plan: {plan.title}",
        "",
        "## Metadata",
        f"- thread_id: {plan.thread_id}",
        f"- mode: {plan.mode}",
        f"- source: {plan.source or ''}",
        f"- client_id: {plan.client_id or ''}",
        f"- overall_status: {plan.overall_status}",
        "",
        "## Objective",
        plan.objective.strip() or "No objective recorded.",
        "",
        "## Active Step",
        f"- step_id: {plan.active_step_id or ''}",
        "",
        "## Steps",
    ]
    for step in plan.steps:
        lines.extend(
            [
                f"### Step {step.step_id}",
                f"- title: {step.title}",
                f"- status: {step.status}",
                f"- owner: {step.owner}",
                f"- allowed_tools: {', '.join(step.allowed_tools)}",
                f"- summary: {step.summary}",
                f"- latest_note: {step.latest_note}",
                "",
            ]
        )
    if not plan.steps:
        lines.append("No steps recorded yet.")
        lines.append("")

    lines.append("## Recent Notes")
    if plan.recent_notes:
        lines.extend(f"- {note}" for note in plan.recent_notes)
    else:
        lines.append("- No execution notes recorded.")
    lines.extend(
        [
            "",
            "## Latest Assistant Summary",
            plan.latest_assistant_summary.strip() or "No assistant summary recorded yet.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_plan_markdown(text: str) -> PlanDocument:
    lines = text.splitlines()
    if not lines or not lines[0].startswith("# Plan: "):
        raise ValueError("Plan markdown is missing the '# Plan:' header")
    title = lines[0][len("# Plan: ") :].strip()

    heading_indices = {}
    for index, line in enumerate(lines):
        if line.startswith("## "):
            heading_indices[line] = index

    required_headings = [
        "## Metadata",
        "## Objective",
        "## Active Step",
        "## Steps",
        "## Recent Notes",
        "## Latest Assistant Summary",
    ]
    for heading in required_headings:
        if heading not in heading_indices:
            raise ValueError(f"Plan markdown is missing required section: {heading}")

    def section_lines(start_heading: str, end_heading: str | None) -> list[str]:
        start = heading_indices[start_heading] + 1
        end = heading_indices[end_heading] if end_heading is not None else len(lines)
        return [line for line in lines[start:end] if line.strip() != ""]

    metadata_lines = section_lines("## Metadata", "## Objective")
    objective_lines = section_lines("## Objective", "## Active Step")
    active_lines = section_lines("## Active Step", "## Steps")
    steps_section_start = heading_indices["## Steps"] + 1
    steps_section_end = heading_indices["## Recent Notes"]
    recent_note_lines = section_lines("## Recent Notes", "## Latest Assistant Summary")
    latest_summary_lines = section_lines("## Latest Assistant Summary", None)

    thread_id = _parse_bullet_value(metadata_lines[0], "thread_id")
    mode = _parse_bullet_value(metadata_lines[1], "mode")
    source = _parse_bullet_value(metadata_lines[2], "source") or None
    client_id = _parse_bullet_value(metadata_lines[3], "client_id") or None
    overall_status = _parse_bullet_value(metadata_lines[4], "overall_status")
    active_step_id = _parse_bullet_value(active_lines[0], "step_id") or None

    step_blocks: list[list[str]] = []
    current_block: list[str] = []
    for line in lines[steps_section_start:steps_section_end]:
        if line.startswith("### Step "):
            if current_block:
                step_blocks.append(current_block)
            current_block = [line]
        elif current_block:
            if line.strip():
                current_block.append(line)
    if current_block:
        step_blocks.append(current_block)

    steps: list[PlanStep] = []
    for block in step_blocks:
        step_id = block[0][len("### Step ") :].strip()
        step = PlanStep(
            step_id=step_id,
            title=_parse_bullet_value(block[1], "title"),
            status=_parse_bullet_value(block[2], "status"),
            owner=_parse_bullet_value(block[3], "owner"),
            allowed_tools=[
                tool.strip()
                for tool in _parse_bullet_value(block[4], "allowed_tools").split(",")
                if tool.strip()
            ],
            summary=_parse_bullet_value(block[5], "summary"),
            latest_note=_parse_bullet_value(block[6], "latest_note"),
        )
        steps.append(step)

    recent_notes = []
    for line in recent_note_lines:
        if line.startswith("- "):
            note = line[2:].strip()
            if note != "No execution notes recorded.":
                recent_notes.append(note)

    return PlanDocument(
        title=title,
        thread_id=thread_id,
        mode=mode,
        source=source,
        client_id=client_id,
        overall_status=overall_status,
        objective="\n".join(objective_lines).strip(),
        active_step_id=active_step_id,
        steps=steps,
        recent_notes=recent_notes,
        latest_assistant_summary="\n".join(latest_summary_lines).strip(),
    )


def looks_like_structured_plan(text: str) -> bool:
    return bool(re.search(r"^# Plan: ", text, re.MULTILINE)) and "## Steps" in text
