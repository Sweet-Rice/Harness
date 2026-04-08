import json
import ollama

from harness.tools.files import read_file, write_file
from harness.tools.shell import run_shell


OUTPUT_SYSTEM_PROMPT = """You are an execution assistant. You are given an approved plan and the user's original intent. Your job is to carry out the plan and produce the deliverable.

INSTRUCTIONS:
- Work through each step of the plan.
- Use tools when the plan requires reading or writing files. Always use absolute paths.
- Use run_shell for bash commands (e.g. running tests, checking structure, installing deps).
- For code generation tasks: write the complete, working code.
- For explanations or summaries: write the full text.
- Do NOT restate or summarize the plan. Produce ONLY the deliverable.
- Your response should contain the final result the user asked for, nothing else."""


OUTPUT_REVIEWER_PROMPT = """You are reviewing an AI agent's output. The user's original request is the source of truth.

You have tools available to verify the output:
- read_file(file_path): Read a file to check its contents. Requires an absolute path.
- run_shell(command, intent, reason): Run bash commands to validate results (e.g. run tests, check syntax, verify files exist).

Use these tools when verification is needed, then give your verdict.

Check:
1. Does the output satisfy what the user originally asked for? This is the most important check.
2. If code was produced, does it have bugs that would cause runtime errors or wrong output?
3. Did the agent follow any constraints the user specified (e.g. "do not write files", "use Python", etc.)?

FAIL if the output does not fulfill the user's request or violates their constraints.
PASS if the user would be satisfied with this output.

Respond EXACTLY like this:

VERDICT: PASS
ISSUES:
- none

Or:

VERDICT: FAIL
ISSUES:
- (one sentence per issue)"""


EXEC_TOOLS = [
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
            "name": "write_file",
            "description": "Propose writing content to a file. Requires an absolute path. User must approve.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the file (e.g. /home/user/file.txt)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                },
                "required": ["file_path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a bash command. Safe read-only commands run immediately.",
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

EXEC_FUNCS = {
    "read_file": read_file,
    "write_file": write_file,
    "run_shell": run_shell,
}

# Review tools — read-only subset
REVIEW_TOOLS = [
    EXEC_TOOLS[0],  # read_file
    EXEC_TOOLS[2],  # run_shell
]

REVIEW_FUNCS = {
    "read_file": read_file,
    "run_shell": run_shell,
}

MAX_INNER_ROUNDS = 10
MAX_REVIEW_ROUNDS = 10


def output(plan: str, intent: str) -> str:
    """Execute an approved plan and produce the deliverable. Can read and write files via tools. Returns the final output."""
    messages = [
        {"role": "system", "content": OUTPUT_SYSTEM_PROMPT},
        {"role": "user", "content": f"## User Intent\n{intent}\n\n## Approved Plan\n{plan}"},
    ]

    proposals = []
    final_text = ""

    for _ in range(MAX_INNER_ROUNDS):
        response = ollama.chat(
            model="qwen3-coder",
            messages=messages,
            tools=EXEC_TOOLS,
        )

        if not response.message.tool_calls:
            final_text = response.message.content
            break

        # Build assistant message with tool calls
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
            func = EXEC_FUNCS.get(tc.function.name)
            if func:
                result = func(**tc.function.arguments)

                # Collect write proposals
                try:
                    parsed = json.loads(result)
                    if isinstance(parsed, dict) and parsed.get("type") == "proposal":
                        proposals.append(parsed)
                        # Tell inner LLM the write is pending approval
                        messages.append({
                            "role": "tool",
                            "content": f"Write to {parsed['path']} proposed — awaiting user approval.",
                        })
                        continue
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

                messages.append({"role": "tool", "content": result})
            else:
                messages.append({"role": "tool", "content": f"Error: unknown tool {tc.function.name}"})

    # Return proposals + text if any writes were proposed
    if proposals:
        return json.dumps({"text": final_text, "proposals": proposals})
    return final_text


def output_review(output: str, plan: str, intent: str) -> str:
    """Review output against the plan and user intent. Can run shell commands and read files to validate. Returns VERDICT: PASS or VERDICT: FAIL with issues."""
    messages = [
        {"role": "system", "content": OUTPUT_REVIEWER_PROMPT},
        {
            "role": "user",
            "content": f"## User Intent\n{intent}\n\n## Approved Plan\n{plan}\n\n## Agent Output\n{output}",
        },
    ]

    for _ in range(MAX_REVIEW_ROUNDS):
        response = ollama.chat(
            model="qwen3-coder",
            messages=messages,
            tools=REVIEW_TOOLS,
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
            func = REVIEW_FUNCS.get(tc.function.name)
            if func:
                result = func(**tc.function.arguments)
                messages.append({"role": "tool", "content": result})
            else:
                messages.append({"role": "tool", "content": f"Error: unknown tool {tc.function.name}"})

    return response.message.content


TOOLS = [output, output_review]
