"""Premade agent definitions for the orchestrator to delegate to.

Each agent is a system prompt + role + tool set.  The supervisor
spawns one at a time via loop().
"""

from dataclasses import dataclass, field


@dataclass
class AgentConfig:
    name: str
    description: str
    system_prompt: str
    role: str                   # maps to a model in harness.toml
    allowed_tools: list[str]
    max_rounds: int = 10


AGENTS: dict[str, AgentConfig] = {
    "planner": AgentConfig(
        name="planner",
        description="Generates and validates step-by-step plans for complex tasks",
        role="orchestrator",
        system_prompt=(
            "You are a planning agent. Given a task:\n"
            "1. Gather context if needed (read_file, web_search, fetch_url).\n"
            "2. Create a numbered, actionable plan using create_plan().\n"
            "3. Validate your plan — check for missing steps, wrong assumptions, edge cases.\n"
            "4. If the plan needs changes, use update_plan() to revise it.\n"
            "5. Return the plan_id and final plan text.\n"
            "\n"
            "RULES:\n"
            "- Only use tools in your tool list.\n"
            "- All file paths must be absolute.\n"
            "- Be specific — each step should be a concrete action, not vague."
        ),
        allowed_tools=[
            "create_plan", "update_plan", "get_plan",
            "read_file", "web_search", "fetch_url",
        ],
    ),
    "coder": AgentConfig(
        name="coder",
        description="Executes coding tasks — reads, writes, and modifies files according to a plan",
        role="coder",
        system_prompt=(
            "You are a coding agent. You receive a plan to execute.\n"
            "1. Read the plan with get_plan() to understand what needs to be done.\n"
            "2. Execute each step using read_file and write_file.\n"
            "3. Update the plan with update_plan() as work progresses.\n"
            "4. When the work is complete, call set_plan_status(plan_id, \"completed\").\n"
            "5. If you cannot complete the work, call set_plan_status(plan_id, \"failed\") and explain the blocker.\n"
            "6. When done, return a concise summary of what you did and any issues encountered.\n"
            "\n"
            "RULES:\n"
            "- Only use tools in your tool list.\n"
            "- All file paths must be absolute.\n"
            "- Follow the plan. If a step is unclear, do your best and note the ambiguity.\n"
            "- Do not claim completion unless you have updated the plan and set its final status."
        ),
        allowed_tools=[
            "read_file", "write_file",
            "get_plan", "update_plan", "set_plan_status",
            "web_search", "fetch_url",
        ],
    ),
}


def get_agent(name: str) -> AgentConfig:
    """Look up a premade agent by name."""
    if name not in AGENTS:
        available = ", ".join(AGENTS.keys())
        raise ValueError(f"Unknown agent: {name}. Available: {available}")
    return AGENTS[name]


def list_agents() -> list[AgentConfig]:
    """Return all registered agents."""
    return list(AGENTS.values())
