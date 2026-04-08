import json
import ollama

from harness.tools.files import read_file
from harness.tools.shell import run_shell


PLAN_SYSTEM_PROMPT = """You are a planning assistant. Given the user's intent, produce a short numbered plan.

You have tools available to explore the codebase before planning:
- read_file(file_path): Read a file's contents. Requires an absolute path.
- run_shell(command, intent, reason): Run bash commands for reconnaissance (ls, find, grep, cat, git status, etc.)

Use these tools FIRST to understand the codebase, then produce your plan.

OUTPUT FORMAT — follow this exactly:
## Plan
1. [First action — what to do and which tool to use, if any]
2. [Second action]
3. ...

RULES:
- Each step is ONE sentence describing an action.
- If a step needs a tool, name the tool. If no tool is needed, say "no tool needed".
- Do NOT include code, code blocks, or implementation details.
- Do NOT solve the problem. Only outline the steps.
- Maximum 10 steps."""


PLAN_REVIEWER_PROMPT = """You are reviewing a task plan. A good plan is a short numbered list of steps. Each step says what to do and which tool to use (if any).

FAIL ONLY if:
- The plan contains a full code implementation (multiple lines of actual code inside ``` blocks). Describing what the code will do in plain English is fine.
- The plan does not address what the user asked for.

PASS everything else. Be lenient. Err on the side of PASS.

Respond EXACTLY like this:

VERDICT: PASS
ISSUES:
- none

Or:

VERDICT: FAIL
ISSUES:
- (one sentence per issue)"""


RECON_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Requires an absolute path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the file (e.g. /home/user/file.txt)",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a bash command for reconnaissance. Safe read-only commands run immediately.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to run",
                    },
                    "intent": {
                        "type": "string",
                        "description": "What the user asked for that led to this command",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why this specific command is needed",
                    },
                },
                "required": ["command", "intent", "reason"],
            },
        },
    },
]

RECON_FUNCS = {
    "read_file": read_file,
    "run_shell": run_shell,
}

MAX_RECON_ROUNDS = 10


def plan(intent: str) -> str:
    """Generate a step-by-step plan to fulfill the user's intent. Can explore the codebase first via tools. Returns a numbered plan."""
    messages = [
        {"role": "system", "content": PLAN_SYSTEM_PROMPT},
        {"role": "user", "content": intent},
    ]

    for _ in range(MAX_RECON_ROUNDS):
        response = ollama.chat(
            model="qwen3-coder",
            messages=messages,
            tools=RECON_TOOLS,
        )

        if not response.message.tool_calls:
            return response.message.content

        assistant_msg = {
            "role": "assistant",
            "content": response.message.content or "",
            "tool_calls": [
                {"function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in response.message.tool_calls
            ],
        }
        messages.append(assistant_msg)

        for tc in response.message.tool_calls:
            func = RECON_FUNCS.get(tc.function.name)
            if func:
                result = func(**tc.function.arguments)
                messages.append({"role": "tool", "content": result})
            else:
                messages.append({"role": "tool", "content": f"Error: unknown tool {tc.function.name}"})

    return response.message.content


def plan_review(plan: str, intent: str) -> str:
    """Review a plan against the user's intent. Returns VERDICT: PASS or VERDICT: FAIL with issues."""
    response = ollama.chat(
        model="qwen3-coder",
        messages=[
            {"role": "system", "content": PLAN_REVIEWER_PROMPT},
            {"role": "user", "content": f"## User Intent\n{intent}\n\n## Agent Plan\n{plan}"},
        ],
    )
    return response.message.content


TOOLS = [plan, plan_review]
